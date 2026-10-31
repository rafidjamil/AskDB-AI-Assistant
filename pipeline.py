"""Phase 7 + 8: Poora workflow ek jagah.

Question -> schema -> LLM(SQL) -> validate -> execute -> LLM(answer)
Agar SQL fail ho jaye to error LLM ko wapas dekar usay khud theek karwata hai
(yeh chhota sa "agent-style" retry loop hai).
"""
from sqlalchemy.exc import SQLAlchemyError

import config
from answer_generator import generate_answer
from database import execute_select, get_database_schema, get_engine, get_table_names
from llm_service import get_llm
from query_parser import UNANSWERABLE, generate_sql
from sql_validator import InvalidSQLError, UnsafeSQLError, validate_sql


def run_pipeline(question: str, llm=None, engine=None) -> dict:
    """Returns dict: status, question, sql, columns, rows, answer, attempts.

    status: ok | blocked | unanswerable | error
    """
    question = (question or "").strip()
    result = {"status": "error", "question": question, "sql": None, "columns": [],
              "rows": [], "answer": "", "attempts": 0}
    if not question:
        result["answer"] = "Please type a question."
        return result

    llm = llm or get_llm()
    engine = engine or get_engine()
    schema = get_database_schema(engine)
    tables = get_table_names(engine)
    dialect = engine.dialect.name

    previous_sql, last_error = None, None
    for attempt in range(1, config.MAX_SQL_RETRIES + 2):
        result["attempts"] = attempt
        raw_sql = generate_sql(question, schema, llm, dialect, previous_sql, last_error)

        if raw_sql.strip().upper().startswith(UNANSWERABLE):
            result.update(status="unanswerable",
                          answer="I can't answer that from this database (or it asks to change data).")
            return result

        result["sql"] = raw_sql
        try:
            safe_sql = validate_sql(raw_sql, tables)
            columns, rows = execute_select(engine, safe_sql)
        except UnsafeSQLError as exc:
            # Khatarnak query: retry nahi, seedha block.
            result.update(status="blocked", answer=f"Blocked for safety: {exc}")
            return result
        except (InvalidSQLError, SQLAlchemyError) as exc:
            previous_sql = raw_sql
            last_error = str(getattr(exc, "orig", exc))
            continue

        result.update(sql=safe_sql, columns=columns, rows=rows)
        result["answer"] = generate_answer(question, safe_sql, rows, llm)
        result["status"] = "ok"
        return result

    result["answer"] = ("Sorry, I couldn't build a working query for that question. "
                        "Try rephrasing it.")
    result["error"] = last_error
    return result
