"""Terminal se poora system chalane ke liye.

  python main.py                      -> interactive mode
  python main.py "Who earns 50,000?"  -> single sawal
"""
import sys

from pipeline import run_pipeline


def show(result: dict) -> None:
    print(f"\n[status: {result['status']} | attempts: {result['attempts']}]")
    if result["sql"]:
        print("SQL     :", result["sql"])
    if result["rows"]:
        print("Records :", result["rows"])
    print("Answer  :", result["answer"], "\n")


def ask(question: str, llm=None) -> None:
    try:
        show(run_pipeline(question, llm=llm))
    except Exception as exc:  # API key / quota / network waghera
        print(f"\nError: {exc}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ask(" ".join(sys.argv[1:]))
    else:
        print("AI Database Assistant. Sawal poochho (quit likh kar band karo).\n")
        while True:
            try:
                q = input("You > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q.lower() in {"quit", "exit", "q"}:
                break
            if q:
                ask(q)
