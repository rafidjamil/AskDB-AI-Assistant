from collections import defaultdict
from datetime import date

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy import create_engine, text

import seed_university as su
from database import create_sample_database, execute_select, get_database_schema, get_engine
from pipeline import run_pipeline
from sql_validator import validate_sql

TODAY = date(2026, 10, 31)


@pytest.fixture(scope="module")
def data():
    return su.generate_dataset(1000, seed=42, today=TODAY)


def test_counts_and_unique_ids(data):
    students, results = data
    assert len(students) == 1000
    assert len({s["student_id"] for s in students}) == 1000
    assert len({s["email"] for s in students}) == 1000
    assert len({s["name"] for s in students}) == 1000      # naam bhi unique
    assert len(results) > 2000


def test_deterministic_with_seed():
    a = su.generate_dataset(100, seed=7, today=TODAY)
    assert a == su.generate_dataset(100, seed=7, today=TODAY)
    assert a != su.generate_dataset(100, seed=8, today=TODAY)


def test_status_and_graduation_rules(data):
    students, _ = data
    statuses = {s["status"] for s in students}
    assert statuses == {"Active", "Graduated", "Withdrawn", "Frozen"}
    for s in students:
        if s["status"] == "Graduated":
            assert s["graduation_date"] is not None and s["graduation_date"] <= TODAY
            assert s["progress_percent"] == 100.0 and s["credits_completed"] == s["total_credits"]
            assert s["cgpa"] >= 2.0
        else:
            assert s["graduation_date"] is None


def test_cgpa_matches_semester_results(data):
    students, results = data
    by_student = defaultdict(list)
    for r in results:
        by_student[r["student_id"]].append(r)
    for s in students:
        rows = sorted(by_student[s["student_id"]], key=lambda r: r["semester_no"])
        if not rows:
            assert s["cgpa"] is None and s["grade"] is None and s["credits_completed"] == 0
            assert s["academic_standing"] == "No Results Yet"
            continue
        assert [r["semester_no"] for r in rows] == list(range(1, len(rows) + 1))
        points = sum(round(r["sgpa"] * 100) * r["credit_hours"] for r in rows)
        credits = sum(r["credit_hours"] for r in rows)
        assert s["cgpa"] == su.weighted_cgpa(points, credits) == rows[-1]["cumulative_cgpa"]
        assert abs(s["cgpa"] - points / credits / 100) <= 0.005 + 1e-9
        assert s["credits_completed"] == sum(r["credits_earned"] for r in rows)


def test_field_consistency(data):
    students, _ = data
    for s in students:
        assert 0 <= (s["cgpa"] or 0) <= 4
        assert 0 <= s["progress_percent"] <= 100
        assert 50 <= s["attendance_percent"] <= 100
        assert 1 <= s["current_semester"] <= 9
        assert s["join_date"].year == s["admission_year"]
        assert s["age"] == today_age(s["date_of_birth"])
        assert 16 <= s["age"] <= 30
        if s["cgpa"] is not None:
            assert s["grade"] == su.letter_grade(s["cgpa"])
            assert s["academic_standing"] == su.standing(s["cgpa"])


def today_age(dob):
    return su.calc_age(dob, TODAY)


def test_programs_only_exist_after_their_launch_batch(data):
    students, _ = data
    first_batch = {p[0]: p[4] for p in su.PROGRAMS}
    for s in students:
        assert s["admission_year"] >= first_batch[s["program"]]
        if s["campus"] == "DCK Campus":
            assert s["program"] in su.DCK_PROGRAMS


def test_seed_into_database_replaces_employees(tmp_path):
    url = f"sqlite:///{(tmp_path / 'u.db').as_posix()}"
    create_sample_database(url)                      # purana employees table bana do
    su.seed(url, 1000, today=TODAY)
    engine = create_engine(url)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM students")).scalar() == 1000
        assert c.execute(text("SELECT COUNT(*) FROM semester_results")).scalar() > 2000
        tables = {r[0] for r in c.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert "employees" not in tables
    # re-seed bhi theek chalna chahiye (drop + create)
    su.seed(url, 50, today=TODAY, drop_employees=False)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM students")).scalar() == 50


def test_keep_employees_flag(tmp_path):
    url = f"sqlite:///{(tmp_path / 'k.db').as_posix()}"
    create_sample_database(url)
    su.seed(url, 20, today=TODAY, drop_employees=False)
    with create_engine(url).connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM employees")).scalar() == 8


@pytest.fixture()
def uni_engine(tmp_path):
    url = f"sqlite:///{(tmp_path / 'uni.db').as_posix()}"
    su.seed(url, 1000, today=TODAY)
    return get_engine(url)


def test_schema_shows_exact_category_values_and_notes(uni_engine):
    schema = get_database_schema(uni_engine)
    assert "Table: students" in schema and "Table: semester_results" in schema
    assert "students.status values: Active | Frozen | Graduated | Withdrawn" in schema
    assert "BS Computer Science" in schema                  # program ki exact values
    assert "students.name values" not in schema             # high-cardinality column skip
    assert "CGPA" in schema and "Notes about the data" in schema


def test_execute_select_returns_plain_json_values(uni_engine):
    _, rows = execute_select(uni_engine, "SELECT student_id, date_of_birth, cgpa FROM students WHERE cgpa IS NOT NULL LIMIT 1")
    r = rows[0]
    assert isinstance(r["date_of_birth"], str) and len(r["date_of_birth"]) == 10
    assert isinstance(r["cgpa"], float)


def test_join_with_aliases_passes_validator_and_runs(uni_engine):
    sql = ("SELECT s.name, r.term, r.sgpa FROM students s JOIN semester_results r "
           "ON s.student_id = r.student_id WHERE s.student_id = 'DSU-2024-0001' ORDER BY r.semester_no")
    assert validate_sql(sql, ["students", "semester_results"])
    llm = FakeListChatModel(responses=[sql, "Here are the semester results."])
    r = run_pipeline("Show semester results of DSU-2024-0001", llm=llm, engine=uni_engine)
    assert r["status"] == "ok" and len(r["rows"]) >= 1 and r["rows"][0]["term"].startswith(("Fall", "Spring"))


def test_graduated_in_2025_style_question(uni_engine):
    sql = "SELECT COUNT(*) AS n FROM students WHERE status = 'Graduated' AND graduation_date >= '2025-01-01' AND graduation_date < '2026-01-01'"
    r = run_pipeline("How many students graduated in 2025?", llm=FakeListChatModel(responses=[sql, "ok"]), engine=uni_engine)
    assert r["status"] == "ok" and r["rows"][0]["n"] > 0


def test_delete_students_is_blocked(uni_engine):
    r = run_pipeline("Delete all students", llm=FakeListChatModel(responses=["DELETE FROM students"]), engine=uni_engine)
    assert r["status"] == "blocked"
    assert execute_select(uni_engine, "SELECT COUNT(*) AS n FROM students")[1] == [{"n": 1000}]
