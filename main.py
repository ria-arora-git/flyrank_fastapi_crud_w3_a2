from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sqlite3
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Server running and connected to Supabase")

app = FastAPI()

DB_NAME = "tasks.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT,
            done INTEGER
        )
    """)

    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

    if count == 0:
        conn.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [
                ("Learn FastAPI", 0),
                ("Build CRUD API", 0),
                ("Test with Swagger", 0)
            ]
        )

    conn.commit()
    conn.close()


init_db()

tasks = [
    {
        "id": 1,
        "title": "Read the doc",
        "done": False
    },
    {
        "id": 2,
        "title": "Understand the steps",
        "done": False
    },
    {
        "id": 3,
        "title": "Build it",
        "done": False
    }
]

@app.get("/", summary="Get API information")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health", summary="Check API health")
def health():
    return {"status": "ok"}

@app.get("/tasks", summary="Get all the tasks")
def get_tasks():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "title": row[1],
            "done": bool(row[2])
        }
        for row in rows
    ]

@app.get("/tasks/{task_id}", summary="Get a specific task")
def get_task(task_id: int):
    conn = sqlite3.connect(DB_NAME)

    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Task not found"}
        )

    return {
        "id": row[0],
        "title": row[1],
        "done": bool(row[2])
    }

@app.post("/tasks", status_code=201, summary="Create a task")
async def create_task(data: dict):
    if "title" not in data or not data["title"]:
        return JSONResponse(
            status_code=400,
            content={"error": "Title is required"}
        )

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (data["title"], 0)
    )

    task_id = cursor.lastrowid

    conn.commit()

    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    conn.close()

    return {
        "id": row[0],
        "title": row[1],
        "done": bool(row[2])
    }

@app.put("/tasks/{task_id}", summary="Update a task")
async def update_task(task_id: int, data: dict | None = None):

    if not data:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid body"}
        )

    if "title" not in data or "done" not in data:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid body"}
        )

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (data["title"], int(data["done"]), task_id)
    )

    if cursor.rowcount == 0:
        conn.close()
        return JSONResponse(
            status_code=404,
            content={"error": "Task not found"}
        )

    conn.commit()

    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    conn.close()

    return {
        "id": row[0],
        "title": row[1],
        "done": bool(row[2])
    }

@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    conn = sqlite3.connect(DB_NAME)

    cursor = conn.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )

    if cursor.rowcount == 0:
        conn.close()
        return JSONResponse(
            status_code=404,
            content={"error": "Task not found"}
        )

    conn.commit()
    conn.close()

    return