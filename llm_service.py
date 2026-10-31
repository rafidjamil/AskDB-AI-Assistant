"""LLM (Gemini) ko LangChain ke through call karne ka kaam.

Phase 2: System prompt + Human prompt -> model -> text response.
"""
import re
import time

from langchain_core.messages import HumanMessage, SystemMessage

import config

# Yeh errors temporary hote hain (server busy / per-minute limit), dobara try karna theek hai
TRANSIENT_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded")


def get_llm():
    """ChatGoogleGenerativeAI ka object banata hai (temperature=0 => stable output)."""
    if not config.GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY nahi mili. Project folder mein .env file banao aur "
            "GOOGLE_API_KEY=... likho (.env.example dekho)."
        )
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        temperature=0,
        api_key=config.GOOGLE_API_KEY,
    )


def message_text(message) -> str:
    """Model ke response se plain text nikalta hai.

    Naye Gemini models 'content' ko blocks ki list bana kar dete hain
    (thinking + text), is liye seedha .content print karna safe nahi.
    """
    text = getattr(message, "text", None)
    if isinstance(text, str):
        return text.strip()
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content.strip()
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts).strip()


def ask_llm(llm, system_prompt: str, human_prompt: str, attempts: int = 4) -> str:
    """System + Human message bhejta hai. 503/429 par thora ruk kar khud dobara try karta hai."""
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
    for attempt in range(1, attempts + 1):
        try:
            return message_text(llm.invoke(messages))
        except Exception as exc:
            msg = str(exc)
            if "PerDay" in msg or "per day" in msg:
                raise RuntimeError(
                    "Gemini ki daily free limit khatam ho gayi. Kal try karo, ya .env mein "
                    "GEMINI_MODEL badlo (e.g. gemini-3.1-flash-lite)."
                ) from exc
            transient = any(marker in msg for marker in TRANSIENT_MARKERS)
            if not transient or attempt == attempts:
                raise
            # 429 mein Google khud batata hai "retry in 18s", warna 5s, 10s, 15s
            found = re.search(r"retry in ([\d.]+)s", msg)
            wait = min(float(found.group(1)) + 1 if found else 5 * attempt, 60)
            print(f"[Gemini busy, {wait:.0f}s baad dobara try hoga ({attempt}/{attempts - 1})]")
            time.sleep(wait)
