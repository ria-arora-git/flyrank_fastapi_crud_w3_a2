from fastapi import FastAPI, Request, Header, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

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

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Access token required")

    token = credentials.credentials

    try:
        response = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = response.user
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user

@app.post("/auth/signup", status_code=201, summary="Create a new user account")
async def signup(data: dict):
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"}
        )

    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )

    return {
        "user": {
            "id": response.user.id,
            "email": response.user.email
        }
    }

@app.post("/auth/login", summary="Authenticate and return a JWT")
async def login(data: dict):
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"}
        )

    try:
        response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid login credentials"}
        )

    return {
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token
    }

@app.get("/public/info", summary="Public info, no auth required")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile", summary="Get the logged-in user's profile")
def get_profile(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "created_at": str(user.created_at)
    }

@app.post("/auth/logout", status_code=204, summary="Log out the current user")
def logout(user=Depends(get_current_user)):
    supabase.auth.sign_out()
    return

@app.get("/protected/dashboard", summary="Example second protected route, reuses the same guard")
def get_dashboard(user=Depends(get_current_user)):
    return {"message": f"Welcome to your dashboard, {user.email}"}

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