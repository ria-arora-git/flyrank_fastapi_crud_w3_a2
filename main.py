from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sqlite3

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

@app.put("/tasks/{task_id}")
async def update_task(task_id: int, data: dict):
    for task in tasks:
        if task["id"] == task_id:
            if not data:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid body"}
                )

            if "title" in data:
                task["title"] = data["title"]

            if "done" in data:
                task["done"] = data["done"]

            return task

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"}
    )

@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
async def delete_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            return

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"}
    )