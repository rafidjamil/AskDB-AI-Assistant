import pytest

from sql_validator import InvalidSQLError, UnsafeSQLError, clean_llm_sql, validate_sql

TABLES = ["employees"]


def test_valid_select_passes():
    sql = "SELECT name FROM employees WHERE salary = 50000;"
    assert validate_sql(sql, TABLES) == "SELECT name FROM employees WHERE salary = 50000"


@pytest.mark.parametrize("sql", [
    "DELETE FROM employees",
    "DROP TABLE employees",
    "UPDATE employees SET salary = 1",
    "INSERT INTO employees VALUES (9, 'x', 1, 'y')",
    "ALTER TABLE employees ADD COLUMN x INT",
    "PRAGMA table_info(employees)",
    "SELECT * FROM employees; DROP TABLE employees",
    "/* hi */ DELETE FROM employees",
    "WITH x AS (SELECT 1) DELETE FROM employees",
    "SELECT * INTO backup FROM employees",
])
def test_dangerous_sql_is_blocked(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql, TABLES)


def test_keyword_inside_string_literal_is_ok():
    assert validate_sql("SELECT * FROM employees WHERE name = 'drop; delete'", TABLES)


def test_column_names_containing_keywords_are_ok():
    assert validate_sql("SELECT created_at, updated_by FROM employees", TABLES)


def test_unknown_table_is_invalid_not_unsafe():
    with pytest.raises(InvalidSQLError):
        validate_sql("SELECT * FROM users", TABLES)


def test_cte_name_is_not_treated_as_unknown_table():
    sql = "WITH rich AS (SELECT * FROM employees WHERE salary > 1) SELECT * FROM rich"
    assert validate_sql(sql, TABLES)


def test_empty_sql():
    with pytest.raises(InvalidSQLError):
        validate_sql("   ", TABLES)


def test_clean_llm_sql_removes_fences():
    assert clean_llm_sql("```sql\nSELECT 1;\n```") == "SELECT 1;"
    assert clean_llm_sql("SELECT 2") == "SELECT 2"
