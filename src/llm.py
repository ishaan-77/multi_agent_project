"""Single entry point for every LLM call in the pipeline.

`call_structured` asks Gemini for output matching a Pydantic schema. If the output is
missing or invalid, it retries (up to LLM_MAX_RETRIES), feeding the error back to the
model. Rate-limit errors back off before retrying. Every attempt is written to the audit
log. If all attempts fail, it raises LLMError and the orchestrator decides how to degrade.
"""
from __future__ import annotations

import time
from typing import Callable, TypeVar

from pydantic import BaseModel

from src.config import GEMINI_MODEL, LLM_MAX_RETRIES, require_api_key
from src.state import AuditEntry

T = TypeVar("T", bound=BaseModel)

_llm_factory: Callable | None = None


class LLMError(Exception):
    def __init__(self, message: str, audit: list[AuditEntry]):
        super().__init__(message)
        self.audit = audit


def set_llm_factory(factory: Callable | None) -> None:
    """Swap the model (tests inject a fake one). Pass None to restore Gemini."""
    global _llm_factory
    _llm_factory = factory


def _make_llm():
    if _llm_factory is not None:
        return _llm_factory()
    from langchain_google_genai import ChatGoogleGenerativeAI

    require_api_key()
    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0)


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc)
    return "429" in text or "RESOURCE_EXHAUSTED" in text or "quota" in text.lower()


def _is_daily_quota(exc: Exception) -> bool:
    """A per-day quota won't reset for hours, so retrying is pointless."""
    return "PerDay" in str(exc)


def call_structured(schema: type[T], system: str, user: str, agent: str) -> tuple[T, list[AuditEntry]]:
    llm = _make_llm().with_structured_output(schema)
    base = [("system", system), ("human", user)]
    messages = list(base)
    audit: list[AuditEntry] = []
    last_error: Exception | None = None
    attempts = LLM_MAX_RETRIES + 1

    for attempt in range(1, attempts + 1):
        started = time.monotonic()
        try:
            result = llm.invoke(messages)
            if result is None:
                raise ValueError("model returned no parseable structured output")
            if isinstance(result, dict):
                result = schema.model_validate(result)
            audit.append(AuditEntry(
                agent=agent, event="llm_call_ok",
                detail=f"attempt {attempt}, {time.monotonic() - started:.1f}s, schema={schema.__name__}",
            ))
            return result, audit
        except Exception as exc:  # noqa: BLE001 - any failure is retryable here
            last_error = exc
            audit.append(AuditEntry(
                agent=agent, event="llm_call_failed",
                detail=f"attempt {attempt}: {type(exc).__name__}: {str(exc)[:300]}",
            ))
            if _is_daily_quota(exc):
                raise LLMError(f"{agent}: daily API quota exhausted, not retrying: {str(exc)[:300]}", audit) from exc
            if attempt == attempts:
                break
            if _is_rate_limit(exc):
                time.sleep(min(5 * 2 ** attempt, 40))
            messages = base + [(
                "human",
                f"Your previous answer could not be used: {str(exc)[:500]}\n"
                f"Return a corrected answer that matches the required schema exactly.",
            )]

    raise LLMError(f"{agent}: failed after {attempts} attempts: {last_error}", audit)
