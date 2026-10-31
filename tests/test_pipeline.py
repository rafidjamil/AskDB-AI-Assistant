import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy.exc import OperationalError

import api
from database import create_sample_database, execute_select, get_database_schema, get_engine
from pipeline import run_pipeline


@pytest.fixture()
def engine(tmp_path):
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    create_sample_database(url)
    return get_engine(url)


def fake(*responses):
    return FakeListChatModel(responses=list(responses))


def test_schema_text_lists_real_columns(engine):
    schema = get_database_schema(engine)
    assert "Table: employees" in schema and "salary" in schema and "department" in schema


def test_happy_path(engine):
    llm = fake("SELECT name FROM employees WHERE salary = 50000",
               "Ali and Sara have a salary of 50,000.")
    r = run_pipeline("Names of employees with salary 50,000?", llm=llm, engine=engine)
    assert r["status"] == "ok"
    assert {row["name"] for row in r["rows"]} == {"Ali", "Sara"}
    assert r["answer"].startswith("Ali and Sara")
    assert r["attempts"] == 1


def test_markdown_fenced_sql_is_cleaned(engine):
    llm = fake("```sql\nSELECT COUNT(*) AS n FROM employees;\n```", "There are 8 employees.")
    r = run_pipeline("How many employees?", llm=llm, engine=engine)
    assert r["status"] == "ok" and r["rows"] == [{"n": 8}]


def test_empty_result_still_answers(engine):
    llm = fake("SELECT name FROM employees WHERE salary = 1", "No matching records were found.")
    r = run_pipeline("Who earns 1?", llm=llm, engine=engine)
    assert r["status"] == "ok" and r["rows"] == [] and "No matching" in r["answer"]


def test_self_correction_after_bad_column(engine):
    llm = fake("SELECT employee_name FROM employees",   # galat column
               "SELECT name FROM employees",            # LLM ne theek kar diya
               "Here are all the names.")
    r = run_pipeline("List names", llm=llm, engine=engine)
    assert r["status"] == "ok" and r["attempts"] == 2 and len(r["rows"]) == 8


def test_unknown_table_triggers_retry(engine):
    llm = fake("SELECT * FROM users", "SELECT name FROM employees LIMIT 1", "One name.")
    r = run_pipeline("List users", llm=llm, engine=engine)
    assert r["status"] == "ok" and r["attempts"] == 2


def test_destructive_request_is_blocked_and_data_survives(engine):
    llm = fake("DELETE FROM employees")
    r = run_pipeline("Delete all employees", llm=llm, engine=engine)
    assert r["status"] == "blocked" and r["attempts"] == 1
    _, rows = execute_select(engine, "SELECT COUNT(*) AS n FROM employees")
    assert rows == [{"n": 8}]


def test_unanswerable_question(engine):
    r = run_pipeline("What's the weather?", llm=fake("UNANSWERABLE"), engine=engine)
    assert r["status"] == "unanswerable"


def test_gives_up_after_max_retries(engine):
    llm = fake("SELECT nope FROM employees")  # hamesha galat
    r = run_pipeline("anything", llm=llm, engine=engine)
    assert r["status"] == "error" and r["attempts"] == 3


def test_database_connection_itself_is_read_only(engine):
    # validator ko bypass bhi kar dein to SQLite query_only mode likhne nahi deta
    with pytest.raises(OperationalError):
        execute_select(engine, "DELETE FROM employees")


def test_empty_question(engine):
    r = run_pipeline("   ", llm=fake("x"), engine=engine)
    assert r["status"] == "error" and r["answer"]


def test_api_endpoint(engine, monkeypatch):
    monkeypatch.setattr(api, "_llm", lambda: fake("SELECT name FROM employees WHERE salary > 100000",
                                                  "Fatima earns more than 100,000."))
    monkeypatch.setattr(api, "_engine", lambda: engine)
    client = TestClient(api.app)

    res = client.post("/api/ask", json={"question": "Who earns over 100,000?"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok" and body["rows"] == [{"name": "Fatima"}]

    assert client.post("/api/ask", json={"question": ""}).status_code == 422
    assert "employees" in client.get("/api/schema").json()["schema"]
    assert "AI Database Assistant" in client.get("/").text
