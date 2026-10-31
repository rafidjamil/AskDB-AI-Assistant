# AskDB AI — AI-Powered Natural Language Database Assistant

> **Personal Project** for Data Science / AI/ML Stream.
> **Approved by:** Tehniyat Mirza (Senior Lecturer, DHA Suffa University).
> **Author:** Rafid Jamil.

---

## Project Overview
        
**AskDB AI** is an advanced, production-ready Natural Language-to-SQL AI Database Assistant. It allows users to ask complex questions in plain English about student records, programs, CGPAs, and academic standings, and automatically translates those questions into safe, executable SQL queries.
![Project Screenshot](./frontend/frontendlook.png)
Instead of writing manual SQL queries, users interact with a modern **ChatGPT / Claude-style Web UI**, which streams execution status step-by-step, retrieves real-time data from a **Neon PostgreSQL Database**, and provides human-readable answers along with transparent, viewable SQL queries and formatted data tables.

---

## Technical Architecture & Pipeline Diagram

The system operates via a decoupled 5-tier architecture connecting the Frontend, FastAPI Backend, LangChain Framework, Google Gemini LLM, and Neon Serverless PostgreSQL.

```
+-----------------------------------------------------------------------------------+
|                                  USER INTERFACE                                   |
|               (Modern Claude/ChatGPT Style UI - index.html / CSS / JS)            |
+----------------------------------------+------------------------------------------+
                                         |
                                HTTP POST /api/ask
                                         v
+-----------------------------------------------------------------------------------+
|                                  FASTAPI BACKEND                                  |
|     (api.py - Handles CORS, Input Validation via Pydantic, Dynamic Route Setup)    |
+----------------------------------------+------------------------------------------+
                                         |
                                Calls run_pipeline()
                                         v
+-----------------------------------------------------------------------------------+
|                             LANGCHAIN ORCHESTRATION PIPELINE                      |
|                                     (pipeline.py)                                 |
|                                                                                   |
|  [Step 1: Schema Contextualization]                                               |
|    - Fetches live DB schema via SQLAlchemy (get_database_schema)                 |
|                                                                                   |
|  [Step 2: SQL Query Generation]                                                   |
|    - Prompts Google Gemini LLM to convert English -> Safe Read-Only SQL           |
|                                                                                   |
|  [Step 3: Query Execution & Validation]                                           |
|    - Executes generated SQL on Neon DB via SQLAlchemy                             |
|                                                                                   |
|  [Step 4: Answer Synthesis]                                                       |
|    - Passes raw query results back to Gemini for natural language response        |
+--------------------+--------------------------------------+-----------------------+
                     |                                      |
         SQL Query   |                                      | Query Results
         Execution   v                                      | Returned
+------------------------------------+      +---------------+-----------------------+
|       NEON POSTGRESQL DATABASE     |      |          GOOGLE GEMINI LLM            |
|  (Cloud Serverless - 1,000 Records)|      |     (Gemini Model via LangChain)      |
+------------------------------------+      +---------------------------------------+
```

### Detailed Pipeline Workflow Explanation:

1. **User Query Input:** The user types a query (e.g., *"How many students are in each program?"*) or clicks a preset chip on the UI.
2. **API Request Dispatch:** The JavaScript frontend sends an asynchronous HTTP POST request (`/api/ask`) containing the query payload.
3. **FastAPI Request Handling:** `api.py` parses and validates the payload using Pydantic schemas (`AskRequest`) and passes it to `pipeline.py`.
4. **Schema Context Injection:** LangChain reads the current structure of the PostgreSQL database tables (columns, data types, primary keys) using SQLAlchemy's inspection engine.
5. **SQL Generation (LLM):** LangChain combines the schema and the user's natural language prompt, sending it to **Google Gemini**. Gemini generates a syntactically correct SQL query.
6. **Query Execution:** The generated SQL is executed securely over the Neon serverless PostgreSQL connection.
7. **Answer Synthesis:** LangChain feeds the raw SQL query result back to Gemini to generate a polished, formal English response.
8. **UI Rendering:** The client receives a structured JSON response containing the plain English answer, the raw generated SQL, and the tabular dataset. The UI displays the response with a smooth shimmer-animation status indicator.

---

## Technology Stack

| Layer | Technology Used |
| :--- | :--- |
| **Frontend** | HTML5, CSS3 (Modern Glassmorphism / Dark Theme), Vanilla JavaScript (ES6+) |
| **Backend API** | FastAPI (Python 3.10+), Uvicorn ASGI Server |
| **Orchestration & AI** | LangChain Framework, Google Gemini API |
| **Database & ORM** | Neon Serverless PostgreSQL, SQLAlchemy, Psycopg2 |
| **Data Validation** | Pydantic v2 |

---

## Step-by-Step Setup & Installation Guide

Follow these exact steps to clone, configure, seed, and run this project locally.

### Step 1: Clone the Repository

Open your terminal or PowerShell and run:

```bash
git clone https://github.com/your-username/AskDB-AI-Assistant.git
cd AskDB-AI-Assistant
```

---

### Step 2: Set Up Virtual Environment

It is recommended to use a Python virtual environment to manage dependencies cleanly.

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### Step 3: Install Required Dependencies

Install all project packages listed in `requirements.txt`:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 4: Environment Variables Setup (`.env`)

Create a `.env` file in the root directory of the project:

```env
# Google Gemini AI API Key
GOOGLE_API_KEY="YOUR_GEMINI_API_KEY_HERE"

# Neon PostgreSQL Database URL
DATABASE_URL="postgresql://username:password@ep-your-endpoint-name.neon.tech/neondb?sslmode=require"
```

---

### Step 5: Seed the Database

Populate your Neon PostgreSQL database with 1,000 synthetic student records for DHA Suffa University demo data:

```bash
python seed_university.py
```

*Expected output:* Successfully created tables and seeded 1,000 student records into the database.

---

### Step 6: Start the FastAPI Server

Launch the ASGI development server using Uvicorn:

```bash
uvicorn api:app --reload
```

*Command Explanation:*
* `api`: Refers to `api.py`.
* `app`: Refers to the `FastAPI()` instance declared inside `api.py`.
* `--reload`: Enables hot-reloading so code updates take effect automatically.

Server terminal output should look like:
```text
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

### Step 7: Open the Application in Browser

Open your browser and navigate to:
**`http://127.0.0.1:8000`**

*(Note: Do not open `index.html` directly from your file explorer using `file:///`, as it will result in CORS / connection errors. Always access it through the FastAPI server URL.)*

---

## Testing Example Queries

Once the UI is running, test the assistant with the following queries:

* `"How many students are in each program?"`
* `"Show the top 10 students by CGPA"`
* `"How many students graduated in 2025?"`
* `"List students on academic probation"`
* `"What is the average CGPA of Computer Science students?"`

---

## Project Directory Structure

```text
AskDB-AI-Assistant/
│
├── frontend/
│   └── index.html          # Modern ChatGPT/Claude style UI (HTML/CSS/JS)
│
├── api.py                  # FastAPI server entry point & route definitions
├── database.py             # Database engine setup & schema inspection logic
├── llm_service.py          # Google Gemini model initialization
├── pipeline.py             # LangChain natural language-to-SQL logic
├── seed_university.py      # Database seeding script (1,000 records)
├── requirements.txt        # Python package dependencies
├── .env                    # Environment configuration (API keys & DB connection)
└── README.md               # Project documentation
```

---

## Project Achievements & Highlights

***Rapid Development:** Designed, implemented, tested, and deployed within **48 hours**.
***Safe Query Execution:** Read-only guardrails to prevent unauthorized database modifications.
***Interactive Interface:** Features step-by-step progress status indicators (*"Analyzing database schema..."* $\rightarrow$ *"Formulating optimal SQL query..."*) with smooth text shimmer effects.
***Full Transparency:** Provides an expandable view showing the exact generated SQL query alongside the raw dataset.