"""Phase 10 (sabse aakhir): FastAPI backend + frontend serve karna.

Chalao:  uvicorn api:app --reload      phir browser mein http://127.0.0.1:8000
"""
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import get_database_schema, get_engine
from llm_service import get_llm
from pipeline import run_pipeline
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Database Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development ke liye sabhi origins allow hain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def _llm():
    return get_llm()


@lru_cache
def _engine():
    return get_engine()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.get("/api/schema")
def schema():
    return {"schema": get_database_schema(_engine())}


@app.post("/api/ask")
def ask(req: AskRequest):
    try:
        return run_pipeline(req.question, llm=_llm(), engine=_engine())
    except RuntimeError as exc:  # e.g. GOOGLE_API_KEY missing
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI/database error: {exc}")


app.mount("/", StaticFiles(directory=Path(__file__).parent / "frontend", html=True), name="frontend")
