"""Test database (company.db) + employees table banata hai.  Chalao:  python setup_db.py"""
import config
from database import create_sample_database, execute_select, get_database_schema, get_engine

if __name__ == "__main__":
    url = create_sample_database()
    print("Database ready:", url)
    engine = get_engine()
    print(get_database_schema(engine))
    _, rows = execute_select(engine, "SELECT * FROM employees")
    for row in rows:
        print(row)
