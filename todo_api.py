import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
app = FastAPI()

connection = sqlite3.connect("todo.db")
cursor = connection.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT,
        is_done INTEGER
    )
""")
connection.commit()
connection.close()

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("Templates/todo.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/tasks")
def tasks():
    connection = sqlite3.connect("todo.db")
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
    connection = sqlite3.connect("todo.db")
    cursor = connection.cursor()

    cursor.execute("INSERT INTO tasks (task, is_done) VALUES (?, 0)", (new_task.task,))

    connection.commit()
    connection.close()

    return {"message": f"Successfully added {new_task.task}!"}

@app.put("/tasks/{task_id}/done")
def mark_done(task_id: int):
    connection = sqlite3.connect("todo.db")
    cursor = connection.cursor()

    cursor.execute("UPDATE tasks SET is_done = 1 WHERE id = ?", (task_id,))

    connection.commit()
    connection.close()

    return {"message": f"Task {task_id} marked as done!"}

@app.get("/todo", response_class=HTMLResponse)
def serve_todo_page():
    with open("templates/todo.html", "r", encoding="utf-8") as f:
        return f.read()

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    connection = sqlite3.connect("todo.db")
    cursor = connection.cursor()

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    connection.commit()
    connection.close()

    return {"message": f"Task {task_id} deleted!"}