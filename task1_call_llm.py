"""TASK 1 (teacher ka pehla kaam): LangChain se LLM ko call karna.

Abhi database nahi, sirf: System prompt + Human prompt -> model -> SQL text.
Chalao:  python task1_call_llm.py
"""
from llm_service import ask_llm, get_llm

SYSTEM_PROMPT = (
    "You are an assistant that converts university-student questions into SQL queries. "
    "Use only this schema: Table students (student_id, name, program, cgpa, status). "
    "Return only the SQL query, nothing else."
)
HUMAN_PROMPT = "Tell me the names of students whose CGPA is above 3.5."

if __name__ == "__main__":
    llm = get_llm()
    print("Question :", HUMAN_PROMPT)
    print("SQL      :", ask_llm(llm, SYSTEM_PROMPT, HUMAN_PROMPT))
