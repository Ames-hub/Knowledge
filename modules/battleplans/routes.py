from fastapi.responses import HTMLResponse, JSONResponse
from library.auth import authbook, require_valid_token
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.database import DB_PATH
from pydantic import BaseModel
import datetime
import sqlite3
import logging
import os

from modules.browser.routes import logbook

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@router.get("/battleplans", response_class=HTMLResponse)
async def show_login(request: Request, token: str = Depends(require_valid_token)):
    logging.info(f"IP {request.client.host} ({authbook.token_owner(token)}) has accessed the battleplans page.")
    return templates.TemplateResponse(
        request,
        "battleplans.html",
    )

@router.get("/api/bps/list", response_class=JSONResponse)
async def list_bps(request: Request, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is listing all battleplans.")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT date FROM battleplans WHERE owner = ?",
            (owner,)
        )
        data = cursor.fetchall()

    parsed_data = {}
    for item in data:
        date = item[0]
        date_obj = datetime.datetime.strptime(date, "%d-%m-%Y")
        parsed_data[date] = {
            "day": date_obj.strftime("%d"),
            "month": date_obj.strftime("%B"),
        }

    return JSONResponse(parsed_data, status_code=200)

def get_bp_exists(date: datetime.datetime):
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM battleplans WHERE date = ?",
                (date.strftime("%d-%m-%Y"),)
            )
            data = cursor.fetchone()
            try:
                return bool(data[0])
            except TypeError:
                return False
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while checking if a battleplan exists: {err}", exception=err)
            return False

@router.get("/api/bps/get/{date}", response_class=JSONResponse)
async def get_bp(request: Request, date: str, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is fetching a battleplan and all its tasks and details for {date}.")
    date = datetime.datetime.strptime(date, "%d-%B-%Y")

    bp_exists = get_bp_exists(date)
    if not bp_exists:
        return JSONResponse(content={"success": False, "error": "Battleplan does not exist."}, status_code=404)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT date, task, is_done, task_id FROM bp_tasks WHERE date = ?",
            (date.strftime("%d-%m-%Y"),)
        )
        data = cursor.fetchall()

    parsed_data = {
        "date": date.strftime("%d-%m-%Y"),
        "tasks": []
    }
    for item in data:
        parsed_data["tasks"].append({
            "text": item[1],
            "done": bool(item[2]),
            "id": item[3]
        })

    return JSONResponse(parsed_data, status_code=200)

class task_state_data(BaseModel):
    task_id: str
    state: bool

@router.post("/api/bps/task/set_status", response_class=JSONResponse)
async def set_task_status(request: Request, data: task_state_data, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is setting the status of task {data.task_id} to {data.state}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE bp_tasks SET is_done = ? WHERE task_id = ?",
                (bool(data.state), int(data.task_id))
            )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while setting the status of a task: {err}", exception=err)
            conn.rollback()
            return JSONResponse(
                content={
                    "success": False,
                    "error": "Database error occurred while setting the status of a task."
                },
                status_code=500
            )

@router.get("/api/bps/create/{date}")
async def create_bp(request: Request, date: str, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is creating a new battleplan for {date}.")
    date = datetime.datetime.strptime(date, "%d-%B-%Y")
    bp_exists = get_bp_exists(date)
    if bp_exists:
        return JSONResponse(content={"success": False, "error": "Battleplan already exists."}, status_code=409)
    else:
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO battleplans (date, owner) VALUES (?, ?)",
                    (date.strftime("%d-%m-%Y"), owner)
                )
                conn.commit()
                return JSONResponse(content={"success": True}, status_code=201)
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while creating a new battleplan: {err}", exception=err)
                conn.rollback()
                return JSONResponse(
                    content={
                        "success": False,
                        "error": "Database error occurred while creating a new battleplan."
                    },
                    status_code=500
                )

@router.get("/api/bps/task/delete/{task_id}")
async def delete_task(request: Request, task_id: str, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is deleting task {task_id}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM bp_tasks WHERE task_id = ?",
                (int(task_id),)
            )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while deleting a task: {err}", exception=err)
            conn.rollback()
            return JSONResponse(
                content={
                    "success": False,
                    "error": "Database error occurred while deleting a task."
                },
                status_code=500
            )

class add_task_data(BaseModel):
    text: str
    date: str

@router.post("/api/bps/task/add")
async def add_task(request: Request, data: add_task_data, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is adding a new task to the battleplan for {data.date}.")
    date = datetime.datetime.strptime(data.date, "%d-%m-%Y")
    bp_exists = get_bp_exists(date)
    if not bp_exists:
        return JSONResponse(content={"success": False, "error": "Battleplan does not exist."}, status_code=404)
    else:
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO bp_tasks (date, task, is_done) VALUES (?, ?, ?)",
                    (date.strftime("%d-%m-%Y"), data.text, False)
                )
                conn.commit()
                return JSONResponse(content={
                    "id": cursor.lastrowid,
                    "text": data.text,
                    "done": False
                }, status_code=201)
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while adding a new task: {err}", exception=err)
                conn.rollback()