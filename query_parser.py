"""Phase 3: Natural language sawal -> SQL query (LLM Call #1)."""
import config
from llm_service import ask_llm
from sql_validator import clean_llm_sql

UNANSWERABLE = "UNANSWERABLE"

SYSTEM_PROMPT = """You are an expert {dialect} SQL assistant that converts a user's question into ONE read-only SQL query.

Database schema (use ONLY these tables and columns, never invent any):
{schema}

Rules:
- Output ONLY the raw SQL query. No explanations, no markdown, no code fences.
- Write a single SELECT statement (a WITH ... SELECT is also fine).
- Never write INSERT, UPDATE, DELETE, DROP, ALTER or any statement that modifies data.
- Numbers like "50,000" must be written without commas (50000).
- For categories (status, program, grade, ...) use the exact values listed in the schema; for searching names use LOWER(column) LIKE LOWER('%text%').
- Use JOIN when a question needs data from more than one table. For "top N" use ORDER BY ... LIMIT N.
- Do not round or cast unless the question asks for it; when rounding, use ROUND(value, 2).
- Always add LIMIT {max_rows} unless the question needs an aggregate (COUNT, SUM, AVG, ...) that returns one row.
- If the question cannot be answered with this schema, or asks you to modify data, output exactly: {unanswerable}"""

RETRY_SUFFIX = """

Your previous query failed.
Previous query: {previous_sql}
Error: {error}
Fix the query and output ONLY the corrected SQL."""


def generate_sql(question: str, schema: str, llm, dialect: str = "SQL",
                 previous_sql: str | None = None, error: str | None = None) -> str:
    """Sawal + schema LLM ko deta hai aur clean SQL (ya UNANSWERABLE) wapas karta hai."""
    system = SYSTEM_PROMPT.format(
        dialect=dialect, schema=schema, max_rows=config.MAX_ROWS, unanswerable=UNANSWERABLE
    )
    human = question
    if previous_sql and error:
        human += RETRY_SUFFIX.format(previous_sql=previous_sql, error=error)

    raw = ask_llm(llm, system, human)
    return clean_llm_sql(raw)
