import os
import sqlite3
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
app = FastAPI()

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

    conn.commit()
    cur.close()
    conn.close()

create_table()

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("Templates/todo.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/tasks")
def tasks():
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
def add_task(new_task: TaskInput):
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()

    cursor.execute("INSERT INTO tasks (task, is_done) VALUES (%s, 0)", (new_task.task,))

    connection.commit()
    connection.close()

    return {"message": f"Successfully added {new_task.task}!"}

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