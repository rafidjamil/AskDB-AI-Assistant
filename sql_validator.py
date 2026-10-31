"""Phase 5: AI ki banayi hui SQL ko execute karne se PEHLE check karna.

Rules:
  1. Sirf ek statement, aur woh SELECT (ya WITH ... SELECT) hona chahiye.
  2. DELETE / DROP / UPDATE / INSERT / ALTER / PRAGMA waghera blocked.
  3. Sirf wohi tables allowed jo database mein maujood hain.

Yaad rakho: yeh check akela kaafi nahi, database user bhi read-only hona chahiye.
"""
import re


class UnsafeSQLError(Exception):
    """Query khatarnak hai (modify karti hai / multiple statements) -> turant block."""


class InvalidSQLError(Exception):
    """Query safe hai magar galat hai (unknown table waghera) -> LLM se dobara try karwa sakte hain."""


FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "truncate", "replace",
    "merge", "grant", "revoke", "attach", "detach", "pragma", "vacuum", "reindex",
    "exec", "execute", "call", "copy", "into", "load_extension", "set",
}

_STRING_LITERAL = re.compile(r"'(?:[^']|'')*'")
_LINE_COMMENT = re.compile(r"--[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_TABLE_REF = re.compile(r"\b(?:from|join)\s+([A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)?)", re.IGNORECASE)
_CTE_NAME = re.compile(r"(?:\bwith\s+(?:recursive\s+)?|,\s*)([A-Za-z_]\w*)\s+as\s*\(", re.IGNORECASE)


def _strip_noise(sql: str) -> str:
    """Comments aur string literals hata deta hai taake keywords ka check sahi ho."""
    sql = _BLOCK_COMMENT.sub(" ", sql)
    sql = _LINE_COMMENT.sub(" ", sql)
    return _STRING_LITERAL.sub("''", sql)


def validate_sql(sql: str, allowed_tables: list[str] | None = None) -> str:
    """Safe ho to saaf-suthri SQL return karta hai, warna exception."""
    if not sql or not sql.strip():
        raise InvalidSQLError("Empty SQL query.")

    cleaned = sql.strip()
    # sirf aakhri semicolon allowed
    cleaned = cleaned.rstrip(";").strip()
    stripped = _strip_noise(cleaned)

    if ";" in stripped:
        raise UnsafeSQLError("Multiple SQL statements are not allowed.")

    if not re.match(r"^\s*(select|with)\b", stripped, re.IGNORECASE):
        raise UnsafeSQLError("Only SELECT queries are allowed.")

    words = set(re.findall(r"[a-z_]+", stripped.lower()))
    bad = sorted(words & FORBIDDEN_KEYWORDS)
    if bad:
        raise UnsafeSQLError(f"Forbidden keyword(s) in query: {', '.join(bad)}")

    if allowed_tables is not None:
        # EXTRACT(YEAR FROM hire_date) aur "IS DISTINCT FROM col" mein FROM ke baad column hota hai, table nahi
        stripped = re.sub(r"\bextract\s*\(\s*\w+\s+from\b", "extract(", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\bdistinct\s+from\b", "distinct_from", stripped, flags=re.IGNORECASE)
        allowed = {t.lower() for t in allowed_tables}
        ctes = {m.lower() for m in _CTE_NAME.findall(stripped)}
        for ref in _TABLE_REF.findall(stripped):
            name = ref.split(".")[-1].lower()
            if name not in allowed and name not in ctes:
                raise InvalidSQLError(f"Unknown table '{ref}'. Available tables: {', '.join(sorted(allowed))}")

    return cleaned


def clean_llm_sql(raw: str) -> str:
    """LLM kabhi kabhi ```sql ... ``` fences ya extra text laga deta hai; usay hata deta hai."""
    text = raw.strip()
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    return text.strip()
