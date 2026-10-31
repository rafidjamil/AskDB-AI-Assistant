"""DHA Suffa University (DEMO / FAKE data) ke 1000 students generate karke database mein daalta hai.

Do tables banti hain:
  students          -> har student ki poori detail (id, name, dob, age, program, cgpa, grade, status ...)
  semester_results  -> har student ke har COMPLETED semester ka SGPA aur cumulative CGPA

Chalao:
  python seed_university.py                  # 1000 students
  python seed_university.py --rows 2000
  python seed_university.py --yes            # confirmation sawal skip
  python seed_university.py --keep-employees # purana employees table na hatao

WARNING: students aur semester_results DROP hoke dobara bante hain (aur default mein employees bhi hat jata hai).
Isay sirf apne TEST database par chalao, teacher ya university ke asli database par kabhi nahi.
Saara data nakli (random) hai, kisi asli student ka nahi.
"""
import argparse
import random
from collections import Counter
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import (
    Column, Date, ForeignKey, Integer, MetaData, Numeric, String, Table,
    create_engine, func, select, text,
)
from sqlalchemy.engine import make_url

import config

# ----------------------------------------------------------------------------- tables
METADATA = MetaData()

students = Table(
    "students", METADATA,
    Column("student_id", String(20), primary_key=True),
    Column("name", String(100), nullable=False),
    Column("gender", String(10), nullable=False),
    Column("date_of_birth", Date, nullable=False),
    Column("age", Integer, nullable=False),
    Column("email", String(120), nullable=False),
    Column("city", String(50), nullable=False),
    Column("program", String(80), nullable=False),
    Column("department", String(60), nullable=False),
    Column("campus", String(30), nullable=False),
    Column("admission_year", Integer, nullable=False),
    Column("join_date", Date, nullable=False),
    Column("current_semester", Integer, nullable=False),
    Column("credits_completed", Integer, nullable=False),
    Column("total_credits", Integer, nullable=False),
    Column("progress_percent", Numeric(5, 2), nullable=False),
    Column("cgpa", Numeric(3, 2)),                      # NULL = abhi koi semester complete nahi hua
    Column("grade", String(3)),                         # CGPA se overall letter grade
    Column("academic_standing", String(30), nullable=False),
    Column("status", String(20), nullable=False),       # Active / Graduated / Withdrawn / Frozen
    Column("graduation_date", Date),                    # "pass-out" date; sirf Graduated ke liye
    Column("scholarship", String(30), nullable=False),
    Column("fee_status", String(20), nullable=False),
    Column("attendance_percent", Numeric(5, 2), nullable=False),
)

semester_results = Table(
    "semester_results", METADATA,
    Column("result_id", Integer, primary_key=True),
    Column("student_id", String(20), ForeignKey("students.student_id"), nullable=False),
    Column("semester_no", Integer, nullable=False),
    Column("term", String(20), nullable=False),         # e.g. "Fall 2024"
    Column("credit_hours", Integer, nullable=False),
    Column("credits_earned", Integer, nullable=False),
    Column("sgpa", Numeric(3, 2), nullable=False),
    Column("cumulative_cgpa", Numeric(3, 2), nullable=False),
)

# ----------------------------------------------------------------------------- reference data
# (program, department, total credit hours, weight, pehli batch jis mein program tha; 0 = hamesha)
PROGRAMS = [
    ("BS Computer Science", "Computer Science", 130, 18, 0),
    ("BS Software Engineering", "Computer Science", 132, 10, 0),
    ("BS Data Science", "Computer Science", 130, 7, 2022),
    ("BS Artificial Intelligence", "Computer Science", 132, 6, 2024),
    ("BS Cyber Security", "Computer Science", 130, 4, 2024),
    ("BE Electrical Engineering", "Electrical Engineering", 136, 9, 0),
    ("BE Mechanical Engineering", "Mechanical Engineering", 136, 9, 0),
    ("BE Civil Engineering", "Civil Engineering", 136, 7, 0),
    ("BBA", "Management Sciences", 130, 12, 0),
    ("BS Accounting & Finance", "Management Sciences", 130, 7, 0),
    ("BS Business Analytics & Programming", "Management Sciences", 130, 3, 2024),
    ("BS Psychology", "Humanities & Social Sciences", 128, 4, 2024),
    ("BS English", "Humanities & Social Sciences", 126, 2, 0),
    ("BS International Relations", "Humanities & Social Sciences", 126, 2, 0),
]
DCK_PROGRAMS = {"BS Computer Science", "BE Civil Engineering"}  # DHA City Karachi campus par sirf yeh

MALE_FIRST = [
    "Ali", "Ahmed", "Hamza", "Bilal", "Usman", "Hassan", "Omar", "Imran", "Faisal", "Kamran",
    "Danish", "Asad", "Saad", "Talha", "Shahid", "Junaid", "Waqas", "Rizwan", "Adeel", "Fahad",
    "Zeeshan", "Haris", "Arslan", "Moiz", "Daniyal", "Shayan", "Abdullah", "Hammad", "Zain", "Rayyan",
    "Taha", "Owais", "Huzaifa", "Mustafa", "Yasir", "Salman", "Ibrahim", "Affan", "Ammar", "Fawad",
    "Raza", "Murtaza", "Noman", "Sohail", "Furqan", "Tariq", "Basit", "Anas", "Sami", "Wahaj",
]
FEMALE_FIRST = [
    "Sara", "Ayesha", "Fatima", "Zainab", "Hira", "Maryam", "Sana", "Noor", "Mahnoor", "Rabia",
    "Iqra", "Laiba", "Amna", "Nimra", "Khadija", "Anam", "Mehwish", "Bushra", "Samina", "Areeba",
    "Esha", "Zara", "Hania", "Minahil", "Alishba", "Dua", "Eman", "Rida", "Sidra", "Tooba",
    "Aiman", "Komal", "Mariam", "Ramsha", "Sadia", "Warda", "Yumna", "Zoya", "Aleena", "Hafsa",
    "Javeria", "Kinza", "Maham", "Nida", "Palwasha", "Rimsha", "Saba", "Tehreem", "Urooj", "Wajiha",
]
LAST_NAMES = [
    "Khan", "Ahmed", "Ali", "Malik", "Sheikh", "Butt", "Siddiqui", "Qureshi", "Raza", "Hussain",
    "Chaudhry", "Mirza", "Iqbal", "Farooq", "Javed", "Aslam", "Baig", "Nawaz", "Rehman", "Shah",
    "Abbasi", "Ansari", "Memon", "Bhatti", "Gill", "Zaidi", "Rana", "Lodhi", "Yousuf", "Hashmi",
    "Soomro", "Jamali", "Kazmi", "Naqvi", "Rizvi", "Saeed", "Tariq", "Usmani", "Waheed", "Zafar",
    "Haider", "Jafri", "Lakhani", "Merchant", "Pasha",
]
CITIES = ["Karachi", "Hyderabad", "Lahore", "Islamabad", "Quetta", "Sukkur", "Peshawar", "Multan", "Larkana", "Faisalabad"]
CITY_WEIGHTS = [72, 7, 5, 4, 3, 3, 2, 2, 1, 1]

GRADE_CUTOFFS = [(3.85, "A"), (3.50, "A-"), (3.17, "B+"), (2.83, "B"), (2.50, "B-"),
                 (2.17, "C+"), (1.83, "C"), (1.50, "C-"), (1.00, "D")]


# ----------------------------------------------------------------------------- helpers
def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def letter_grade(cgpa: float) -> str:
    for cutoff, grade in GRADE_CUTOFFS:
        if cgpa >= cutoff:
            return grade
    return "F"


def standing(cgpa) -> str:
    if cgpa is None:
        return "No Results Yet"
    if cgpa >= 3.5:
        return "Honor Roll"
    if cgpa >= 2.0:
        return "Good Standing"
    return "Academic Probation"


def term_bounds(batch: int, k: int) -> tuple[date, date]:
    """Semester k (1 se shuru) ki (start, end) date. Odd = Fall (Sep-Jan), even = Spring (Feb-Jun)."""
    j = (k - 1) // 2
    if k % 2 == 1:
        return date(batch + j, 9, 1), date(batch + j + 1, 1, 20)
    return date(batch + j + 1, 2, 1), date(batch + j + 1, 6, 20)


def term_name(batch: int, k: int) -> str:
    start = term_bounds(batch, k)[0]
    return f"{'Fall' if k % 2 == 1 else 'Spring'} {start.year}"


def weighted_cgpa(points_hundredths: int, credit_hours: int) -> float:
    """Credit-weighted average, exact decimal math + half-up rounding (database ke ROUND jaisa)."""
    value = Decimal(points_hundredths) / Decimal(credit_hours) / 100
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calc_age(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


# ----------------------------------------------------------------------------- generator
def generate_dataset(count: int = 1000, seed: int = 42, today: date | None = None):
    """Returns (student_rows, result_rows). Pure function => asaani se test ho jati hai."""
    rng = random.Random(seed)
    today = today or date.today()

    batches = [y for y in range(today.year - 5, today.year + 1) if date(y, 9, 1) <= today]
    weights = [0.07, 0.16, 0.20, 0.22, 0.20, 0.15][-len(batches):]

    used_names: set[tuple[str, str]] = set()
    seq: Counter = Counter()
    student_rows: list[dict] = []
    result_rows: list[dict] = []

    for _ in range(count):
        batch = rng.choices(batches, weights=weights)[0]
        seq[batch] += 1
        student_id = f"DSU-{batch}-{seq[batch]:04d}"

        eligible = [p for p in PROGRAMS if p[4] <= batch]
        program, department, total_credits, _w, _since = rng.choices(eligible, weights=[p[3] for p in eligible])[0]
        campus = "DCK Campus" if program in DCK_PROGRAMS and rng.random() < 0.2 else "Main Campus"

        gender = rng.choice(["Male", "Female"])
        firsts = MALE_FIRST if gender == "Male" else FEMALE_FIRST
        for _try in range(30):
            first, last = rng.choice(firsts), rng.choice(LAST_NAMES)
            if (first, last) not in used_names:
                break
        used_names.add((first, last))

        age_at_admission = rng.choices([17, 18, 19, 20, 21], weights=[2, 6, 5, 2, 1])[0]
        dob = date(batch - age_at_admission, rng.randint(1, 12), rng.randint(1, 28))
        join_date = min(date(batch, 9, 1) + timedelta(days=rng.randint(-14, 7)), today)

        # ---- lifecycle: kitne semester shuru/complete hue, aur status kya hai
        delayed = rng.random() < 0.08                       # 9 semesters lagenge
        n_req = 9 if delayed else 8
        started = [k for k in range(1, n_req + 1) if term_bounds(batch, k)[0] <= today]
        completed = [k for k in started if term_bounds(batch, k)[1] <= today]
        current = len(started)
        result_sems = completed
        status, graduation_date = "Active", None
        if rng.random() < 0.05:
            status = "Withdrawn"
            current = rng.randint(1, len(started))
            result_sems = [k for k in completed if k < current]
        elif len(completed) == n_req:
            status = "Graduated"
            graduation_date = min(term_bounds(batch, n_req)[1] + timedelta(days=rng.randint(10, 50)), today)
        elif current >= 2 and rng.random() < 0.03:
            status = "Frozen"

        # ---- academic performance
        if status == "Graduated":      # graduate hone ke liye CGPA >= 2.0 chahiye
            ability, floor = clamp(rng.gauss(3.05, 0.40), 2.3, 3.98), 2.0
        elif status == "Withdrawn":
            ability, floor = clamp(rng.gauss(2.10, 0.60), 0.9, 3.5), 0.0
        else:
            ability, floor = clamp(rng.gauss(2.90, 0.55), 1.2, 3.98), 0.0

        base, extra = divmod(total_credits, 8)
        deficit_sem = rng.randint(3, 7) if delayed else None
        deficit = rng.choice([3, 6])
        cum_points, cum_credits, earned_total, cgpa = 0, 0, 0, None   # cum_points hundredths mein (exact)

        for k in result_sems:
            credit_hours = deficit if k == 9 else base + (1 if k <= extra else 0)
            sgpa = round(clamp(ability + rng.gauss(0, 0.28) - (0.1 if k == 1 else 0.0), floor, 4.0), 2)
            earned = credit_hours
            if k == deficit_sem:
                earned = max(0, credit_hours - deficit)      # ek course fail, baad mein retake
            elif sgpa < 1.7:
                earned = max(0, credit_hours - 3)
            cum_points += round(sgpa * 100) * credit_hours
            cum_credits += credit_hours
            earned_total += earned
            cgpa = weighted_cgpa(cum_points, cum_credits)
            result_rows.append({
                "result_id": len(result_rows) + 1, "student_id": student_id, "semester_no": k,
                "term": term_name(batch, k), "credit_hours": credit_hours, "credits_earned": earned,
                "sgpa": sgpa, "cumulative_cgpa": cgpa,
            })

        # ---- baqi fields
        if status in ("Graduated", "Withdrawn"):
            fee_status = "Cleared"
        elif status == "Frozen":
            fee_status = "Pending"
        else:
            fee_status = rng.choices(["Paid", "Pending"], weights=[80, 20])[0]

        if cgpa is not None and cgpa >= 3.5 and rng.random() < 0.35:
            scholarship = "Merit"
        else:
            scholarship = rng.choices(["No Scholarship", "Merit", "Need-Based", "Sports"], weights=[75, 8, 14, 3])[0]

        student_rows.append({
            "student_id": student_id,
            "name": f"{first} {last}",
            "gender": gender,
            "date_of_birth": dob,
            "age": calc_age(dob, today),
            "email": f"{first.lower()}.{last.lower()}{seq[batch]}@students.example.com",
            "city": rng.choices(CITIES, weights=CITY_WEIGHTS)[0],
            "program": program,
            "department": department,
            "campus": campus,
            "admission_year": batch,
            "join_date": join_date,
            "current_semester": current,
            "credits_completed": earned_total,
            "total_credits": total_credits,
            "progress_percent": round(min(100.0, 100.0 * earned_total / total_credits), 2),
            "cgpa": cgpa,
            "grade": letter_grade(cgpa) if cgpa is not None else None,
            "academic_standing": standing(cgpa),
            "status": status,
            "graduation_date": graduation_date,
            "scholarship": scholarship,
            "fee_status": fee_status,
            "attendance_percent": round(clamp(rng.gauss(85 + (ability - 2.9) * 6, 6), 50, 100), 2),
        })

    return student_rows, result_rows


# ----------------------------------------------------------------------------- database
def seed(url: str, count: int = 1000, seed_value: int = 42, drop_employees: bool = True,
         today: date | None = None) -> None:
    engine = create_engine(url)
    student_rows, result_rows = generate_dataset(count, seed_value, today)
    with engine.begin() as conn:  # ek transaction: ya sab insert hoga ya kuch nahi
        if drop_employees:
            conn.execute(text("DROP TABLE IF EXISTS employees"))
        METADATA.drop_all(conn)       # pehle semester_results, phir students (FK order khud sambhalta hai)
        METADATA.create_all(conn)
        for i in range(0, len(student_rows), 500):
            conn.execute(students.insert(), student_rows[i:i + 500])
        for i in range(0, len(result_rows), 1000):
            conn.execute(semester_results.insert(), result_rows[i:i + 1000])

    with engine.connect() as conn:
        n_students = conn.execute(select(func.count()).select_from(students)).scalar()
        n_results = conn.execute(select(func.count()).select_from(semester_results)).scalar()
        by_status = conn.execute(select(students.c.status, func.count()).group_by(students.c.status)
                                 .order_by(func.count().desc())).all()
        by_program = conn.execute(
            select(students.c.program, func.count(), func.avg(students.c.cgpa))
            .group_by(students.c.program).order_by(func.count().desc())).all()
        sample = conn.execute(select(students).order_by(students.c.student_id).limit(3)).mappings().all()
    engine.dispose()

    print(f"\nDone. students: {n_students} rows | semester_results: {n_results} rows\n")
    print("Status wise:", ", ".join(f"{s} {n}" for s, n in by_status))
    print("\nProgram wise (students, average CGPA):")
    for program, n, avg in by_program:
        print(f"  {program:<38} {n:>4}   {float(avg):.2f}" if avg is not None else f"  {program:<38} {n:>4}   -")
    print("\nPehle 3 students:")
    for row in sample:
        print("  ", dict(row))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DHA Suffa University demo students data database mein daalo")
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--yes", action="store_true", help="confirmation sawal skip karo")
    parser.add_argument("--keep-employees", action="store_true", help="purana employees table na hatao")
    args = parser.parse_args()

    target = make_url(config.DATABASE_URL).render_as_string(hide_password=True)
    print(f"Target database : {target}")
    print(f"Students        : {args.rows}")
    print("Dhyan: 'students' aur 'semester_results' tables DROP hoke dobara banengi"
          + ("." if args.keep_employees else ", aur purana 'employees' table hata diya jayega."))
    if not args.yes and input("Aage barhna hai? (yes/no): ").strip().lower() != "yes":
        raise SystemExit("Cancelled.")
    seed(config.DATABASE_URL, args.rows, args.seed, drop_employees=not args.keep_employees)
