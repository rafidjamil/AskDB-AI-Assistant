"""Database connection, schema reading aur safe query execution (SQLAlchemy).

Phase 4 + 5.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.types import String

import config

MAX_LISTED_VALUES = 25          # itni ya kam alag values hon to schema mein dikhayenge
_SCHEMA_CACHE: dict[str, str] = {}

SAMPLE_EMPLOYEES = [
    # (employee_id, name, salary, department)
    (1, "Ali", 50000, "Sales"),
    (2, "Ahmed", 80000, "Engineering"),
    (3, "Sara", 50000, "HR"),
    (4, "Hamza", 100000, "Engineering"),
    (5, "Ayesha", 65000, "Marketing"),
    (6, "Bilal", 80000, "Sales"),
    (7, "Fatima", 120000, "Engineering"),
    (8, "Usman", 45000, "HR"),
]


def get_engine(url: str | None = None):
    """Query chalane wala engine. SQLite par READ-ONLY mode force hota hai."""
    engine = create_engine(url or config.DATABASE_URL, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _read_only(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA query_only = ON")

    return engine


def create_sample_database(url: str | None = None) -> str:
    """Test database + employees table banata hai (writable engine, sirf setup ke liye)."""
    engine = create_engine(url or config.DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS employees"))
        conn.execute(
            text(
                "CREATE TABLE employees ("
                "employee_id INTEGER PRIMARY KEY, "
                "name VARCHAR(100) NOT NULL, "
                "salary INTEGER NOT NULL, "
                "department VARCHAR(50))"
            )
        )
        conn.execute(
            text(
                "INSERT INTO employees (employee_id, name, salary, department) "
                "VALUES (:id, :name, :salary, :dept)"
            ),
            [dict(id=i, name=n, salary=s, dept=d) for i, n, s, d in SAMPLE_EMPLOYEES],
        )
    engine.dispose()
    return str(url or config.DATABASE_URL)


def get_table_names(engine) -> list[str]:
    return inspect(engine).get_table_names()


def _column_values(conn, engine, table: str, column: str) -> list[str] | None:
    """Text column ki alag-alag values (agar kam hon), warna None. e.g. status -> Active, Graduated ..."""
    prep = engine.dialect.identifier_preparer
    sql = f"SELECT DISTINCT {prep.quote(column)} FROM {prep.quote(table)} " \
          f"WHERE {prep.quote(column)} IS NOT NULL ORDER BY 1 LIMIT {MAX_LISTED_VALUES + 1}"
    values = [str(row[0]) for row in conn.execute(text(sql))]
    return values if len(values) <= MAX_LISTED_VALUES else None


def get_database_schema(engine) -> str:
    """Tables + columns + (kam-values wale text columns ki exact values) + schema_notes.txt.

    LLM ko exact naam aur exact values pata hon, to galat WHERE (jaise 'CS' ki jagah 'BS Computer Science') nahi banta.
    Result cache hota hai; data dobara seed karo to app restart kar do.
    """
    key = str(engine.url)
    if key in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[key]

    insp = inspect(engine)
    lines = []
    with engine.connect() as conn:
        for table in insp.get_table_names():
            columns = insp.get_columns(table)
            lines.append(f"Table: {table} (" + ", ".join(f"{c['name']} {c['type']}" for c in columns) + ")")
            for col in columns:
                if isinstance(col["type"], String):
                    values = _column_values(conn, engine, table, col["name"])
                    if values:
                        lines.append(f"  {table}.{col['name']} values: " + " | ".join(values))

    notes_file = config.BASE_DIR / "schema_notes.txt"
    if notes_file.exists():
        lines.append("\nNotes about the data:\n" + notes_file.read_text(encoding="utf-8").strip())

    _SCHEMA_CACHE[key] = "\n".join(lines)
    return _SCHEMA_CACHE[key]


def _plain(value):
    """Decimal -> float, date -> 'YYYY-MM-DD' (print aur JSON dono saaf rahein)."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):          # datetime bhi date ki subclass hai
        return value.isoformat()
    return value


def execute_select(engine, sql: str, max_rows: int | None = None):
    """Validated SELECT chalata hai. Returns (column_names, list_of_dict_rows)."""
    limit = max_rows or config.MAX_ROWS
    with engine.connect() as conn:
        if engine.dialect.name in ("postgresql", "mysql"):
            # extra safety: validator chook bhi jaye to yeh transaction likhne nahi dega
            conn.execute(text("SET TRANSACTION READ ONLY"))
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [{c: _plain(v) for c, v in zip(columns, row)} for row in result.fetchmany(limit)]
    return columns, rows
