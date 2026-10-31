import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine, text

import config
import llm_service
import seed_data
from sql_validator import InvalidSQLError, validate_sql

TABLES = ["employees"]



def test_seed_creates_2000_realistic_rows(tmp_path):
    url = f"sqlite:///{(tmp_path / 's.db').as_posix()}"
    seed_data.seed(url, 2000)
    engine = create_engine(url)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM employees")).scalar() == 2000
        assert c.execute(text("SELECT COUNT(DISTINCT employee_id) FROM employees")).scalar() == 2000
        assert c.execute(text("SELECT COUNT(*) FROM employees WHERE salary % 5000 != 0")).scalar() == 0
        assert c.execute(text("SELECT COUNT(*) FROM employees WHERE salary = 50000")).scalar() > 5


def test_seed_is_reproducible():
    assert seed_data.generate_rows(50, seed=1) == seed_data.generate_rows(50, seed=1)
    assert seed_data.generate_rows(50, seed=1) != seed_data.generate_rows(50, seed=2)



def test_extract_from_column_is_not_a_table():
    sql = "SELECT COUNT(*) FROM employees WHERE EXTRACT(YEAR FROM hire_date) = 2023"
    assert validate_sql(sql, TABLES)


def test_real_unknown_table_still_caught_after_extract_fix():
    with pytest.raises(InvalidSQLError):
        validate_sql("SELECT EXTRACT(YEAR FROM hire_date) FROM users", TABLES)



@pytest.mark.parametrize("given,expected_start", [
    ("postgresql://u:p@h/db?sslmode=require", "postgresql+psycopg2://u:p@h/db"),
    ("postgres://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
    ("mysql://u:p@h/db", "mysql+pymysql://u:p@h/db"),
    ("postgresql+psycopg2://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
])
def test_db_url_normalisation(given, expected_start):
    assert config._normalise_db_url(given).startswith(expected_start)


def test_relative_sqlite_path_becomes_absolute():
    assert config._normalise_db_url("sqlite:///company.db").endswith("/company.db")
    assert str(config.BASE_DIR.as_posix()) in config._normalise_db_url("sqlite:///company.db")



class Flaky:
    def __init__(self, errors):
        self.errors, self.calls = list(errors), 0

    def invoke(self, _msgs):
        self.calls += 1
        if self.errors:
            raise Exception(self.errors.pop(0))
        return AIMessage(content="SELECT 1")


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(llm_service.time, "sleep", lambda s: None)


def test_503_is_retried():
    llm = Flaky(["503 UNAVAILABLE", "503 UNAVAILABLE"])
    assert llm_service.ask_llm(llm, "s", "h") == "SELECT 1" and llm.calls == 3


def test_daily_quota_fails_fast_with_clear_message():
    llm = Flaky(["429 RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel-FreeTier"] * 5)
    with pytest.raises(RuntimeError, match="daily free limit"):
        llm_service.ask_llm(llm, "s", "h")
    assert llm.calls == 1


def test_per_minute_429_is_retried():
    llm = Flaky(["429 RESOURCE_EXHAUSTED GenerateRequestsPerMinutePerProjectPerModel retry in 18.0s"])
    assert llm_service.ask_llm(llm, "s", "h") == "SELECT 1" and llm.calls == 2


def test_other_errors_are_not_retried():
    llm = Flaky(["400 API key not valid"] * 3)
    with pytest.raises(Exception, match="API key"):
        llm_service.ask_llm(llm, "s", "h")
    assert llm.calls == 1
