"""Saari settings yahan se load hoti hain (.env file se)."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

def _normalise_db_url(url: str) -> str:
    """Relative SQLite path (sqlite:///company.db) ko project folder ke andar absolute bana deta hai."""
    # Neon/Supabase "postgresql://..." ya "postgres://..." dete hain; hum psycopg2 driver use karte hain
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg2://" + url[len(prefix):]
    # mysql://  ->  mysql+pymysql://
    if url.startswith("mysql://"):
        url = "mysql+pymysql://" + url[len("mysql://"):]
    u = make_url(url)
    if u.drivername.startswith("sqlite") and u.database and u.database != ":memory:":
        path = Path(u.database)
        if not path.is_absolute():
            u = u.set(database=(BASE_DIR / path).as_posix())
    return u.render_as_string(hide_password=False)


DATABASE_URL = _normalise_db_url(os.getenv("DATABASE_URL") or "sqlite:///company.db")

MAX_ROWS = int(os.getenv("MAX_ROWS", "100"))
MAX_SQL_RETRIES = int(os.getenv("MAX_SQL_RETRIES", "2"))
