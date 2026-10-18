"""Smoke test: confirms your Gemini key and model work before building agents.

Run from the project root:  python -m scripts.check_gemini
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from src.config import GEMINI_MODEL, require_api_key


class Ping(BaseModel):
    status: str
    model_note: str


def main() -> None:
    require_api_key()
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0)

    print(f"Model: {GEMINI_MODEL}")
    print("Plain call ->", llm.invoke("Reply with exactly: OK").content)

    # Structured output is what every agent will rely on, so test it too.
    structured = llm.with_structured_output(Ping)
    result = structured.invoke("Return status='OK' and a short note about yourself.")
    print("Structured call ->", result)


if __name__ == "__main__":
    main()
