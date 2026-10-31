"""Phase 6: Database ke result ko dobara human-readable jawab mein badalna (LLM Call #2)."""
import json

from llm_service import ask_llm

SYSTEM_PROMPT = """You are a helpful assistant. Answer the user's question using ONLY the database results provided.
- If the results are empty, clearly say that no matching records were found.
- Do not invent facts or use outside knowledge.
- Be concise (1-3 sentences). Format numbers with thousands separators.
- Answer in the same language as the user's question."""


def generate_answer(question: str, sql: str, rows: list[dict], llm) -> str:
    human = (
        f"Question: {question}\n\n"
        f"SQL that was run: {sql}\n\n"
        f"Database results (JSON): {json.dumps(rows, default=str, ensure_ascii=False)}"
    )
    return ask_llm(llm, SYSTEM_PROMPT, human)
