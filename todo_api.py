import os
import sqlite3
import psycopg2
import datetime
from pydantic import BaseModel
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
app = FastAPI()

SECRET_KEY = "musa_ultra_secret_key"
ALGORITHM = "HS256"

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("Warning: DATABASE_URL not set. Make sure to add it in Railway.")

def create_table():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            task TEXT,
            is_done INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("Templates/todo.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/tasks")
def get_tasks(username: str = Depends(verify_token)):
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()

    cursor.execute("SELECT id, task, is_done FROM tasks")
    rows = cursor.fetchall()

    connection.close()

    task = []
    for row in rows:
        task.append({
            "id": row[0], 
            "task": row[1],
            "is_done": row[2]
        })

    return task

class TaskInput(BaseModel):
    task: str

@app.post("/add_task")
def add_task(new_task: TaskInput, username: str = Depends(verify_token)):
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()

    cursor.execute("INSERT INTO tasks (task, is_done) VALUES (%s, 0)", (new_task.task,))

    connection.commit()
    connection.close()

    return {"message": f"Successfully added {new_task.task}!"}

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

@app.put("/tasks/{task_id}/done")
def mark_done(task_id: int):
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()

    cursor.execute("UPDATE tasks SET is_done = 1 WHERE id = %s", (task_id,))

    connection.commit()
    connection.close()

    return {"message": f"Task {task_id} marked as done!"}

@app.get("/todo", response_class=HTMLResponse)
def serve_todo_page():
    with open("Templates/todo.html", "r", encoding="utf-8") as f:
        return f.read()

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()

    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))

    connection.commit()
    connection.close()

    return {"message": f"Task {task_id} deleted!"}

@app.get("/setup_db")
def setup_db():
    try:
        create_table()
        return {"message": "Databade and table created successfully!"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/register")
def register(user: UserCreate):
    connection = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = connection.cursor()

    hashed_pw = hash_password(user.password)

    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (user.username, hashed_pw)
        )
        connection.commit()
        return {"message": "User registered successfully!"}
    except psycopg2.errors.UniqueViolation:
        connection.rollback()
        return {"error": "username already exists!"}
    finally:
        connection.close()

@app.post("/login")
def login(user: UserLogin):
    connection = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = connection.cursor()

    cursor.execute("SELECT password FROM users WHERE username = %s", (user.username,))
    result = cursor.fetchone()
    connection.close()

    if not result:
        return {"error": "User not found!"}

    stored_hash_password = result[0]
    if not verify_password(user.password, stored_hash_password):
        return {"error": "Incorrect Password!"}

    token = create_access_token({"username": user.username})

    return {"message": "Login Successful!", "token": token}