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

def get_bp_exists(date: datetime.datetime, owner):
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM battleplans WHERE date = ? AND owner = ?",
                (date.strftime("%d-%m-%Y"), owner,)
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

    bp_exists = get_bp_exists(date, owner)
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
    bp_exists = get_bp_exists(date, owner)
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
    bp_exists = get_bp_exists(date, owner)
    if not bp_exists:
        return JSONResponse(content={"success": False, "error": "Battleplan does not exist."}, status_code=404)
    else:
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO bp_tasks (date, task, is_done, owner) VALUES (?, ?, ?, ?)",
                    (date.strftime("%d-%m-%Y"), data.text, False, owner)
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

def dateformatenforcer(date):
    date = date.lower()
    if len(date) > 10:  # If greater than 10 characters, it's probably a month name.
        month_list = {
            "january": "01", "february": "02", "march": "03", "april": "04", "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12",
        }
        for month in month_list.keys():
            if month in date:
                # Replace the month with its number.
                date = date.replace(month, str(month_list[month]))
    else:
        # If the date is less than 10 characters, it's probably a day number.
        date = date #  Dont verify

    return date

class quota_data_set(BaseModel):
    date: str
    amount: float|int

class quota_data_get(BaseModel):
    date: str

def get_quota_exists(date, owner):
    date = dateformatenforcer(date)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bp_quotas WHERE date = ? AND owner = ?",
                (date, owner)
            )
            data = cursor.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while checking if a quota exists: {err}", exception=err)
            return False

    return data is not None

@router.post("/api/bps/quota/set")
async def set_quota(request: Request, data: quota_data_set, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is setting the quota amount for {data.date}.")
    data.date = dateformatenforcer(data.date)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            if get_quota_exists(data.date, owner) is False:
                cursor.execute(
                    """
                    INSERT INTO bp_quotas (date, amount, owner) VALUES (?, ?, ?)
                    """,
                    (data.date, data.amount, owner)
                )
            else:
                cursor.execute(
                    """
                    UPDATE bp_quotas SET amount = ? WHERE date = ? AND owner = ?
                    """,
                    (data.amount, data.date, owner)
                )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while setting the quota amount: {err}", exception=err)
            conn.rollback()
            return JSONResponse(
                content={"success": False, "error": "Database error occurred while modifying finances."},
                status_code=500
            )

@router.post("/api/bps/quota/get")
async def get_quota_needed(request: Request, data: quota_data_get, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is getting the quota amount for {data.date}.")
    data.date = dateformatenforcer(data.date)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT amount FROM bp_quotas WHERE date = ? AND owner = ?",
                (data.date, owner)
            )
            data = cursor.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while fetching the quota amount: {err}", exception=err)
            conn.rollback()
            return HTMLResponse(
                content="Database error occurred while fetching the quota amount.",
                status_code=500
            )

        if not data:
            return HTMLResponse(content="0", status_code=200)

        return HTMLResponse(content=str(data[0]), status_code=200)

def get_done_quota_exists(date, owner):
    date = dateformatenforcer(date)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bp_quotas_done WHERE date = ? AND owner = ?",
                (date, owner)
            )
            data = cursor.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while checking if done quota {date}, {owner} exists: {err}", exception=err)
            return False

    return data is not None

@router.post("/api/bps/quota/done/set")
async def set_quota_done(request: Request, data: quota_data_set, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is setting how much was done for {data.date}")
    data.date = dateformatenforcer(data.date)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            if get_done_quota_exists(data.date, owner) is False:
                cursor.execute(
                    """
                    INSERT INTO bp_quotas_done (date, amount_done, owner) VALUES (?, ?, ?)
                    """,
                    (data.date, data.amount, owner)
                )
            else:
                cursor.execute(
                    """
                    UPDATE bp_quotas_done SET amount_done = ? WHERE date = ? AND owner = ?
                    """,
                    (data.amount, data.date, owner)
                )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while setting the quota amount: {err}", exception=err)
            conn.rollback()
            return JSONResponse(
                content={"success": False, "error": "Database error occurred while modifying finances."},
                status_code=500
            )

def get_quota_done_helper(date, owner):
    date = dateformatenforcer(date)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT amount_done FROM bp_quotas_done WHERE date = ? AND owner = ?",
                (date, owner)
            )
            data = cursor.fetchone()
            return data[0] if data else 0
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while fetching the quota amount: {err}", exception=err)
            conn.rollback()
            return HTMLResponse(
                content="Database error occurred while fetching the quota amount.",
                status_code=500
            )

@router.post("/api/bps/quota/done/get")
async def get_quota_done(request: Request, data: quota_data_get, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is fetching the production metric for {data.date}.")
    quota_done = get_quota_done_helper(data.date, owner)

    if not quota_done:
        return HTMLResponse(content="0", status_code=200)

    return HTMLResponse(content=str(quota_done), status_code=200)

@router.post("/api/bps/quota/weekly")
async def get_weekly_production(request: Request, data: quota_data_get, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is fetching the weekly production metric for {data.date} and 7 days before.")

    data.date = dateformatenforcer(data.date)

    try:
        date = datetime.datetime.strptime(data.date, "%d-%m-%Y")
    except ValueError:
        return HTMLResponse(
            content="Invalid date format. Please use the format DD-MM-YYYY.",
            status_code=400
        )
    dates_list = []
    counter = 0
    # Get the day and the 6 days prior to it in a list.
    while counter != 7:
        dates_list.append(date.strftime("%d-%m-%Y"))
        date -= datetime.timedelta(days=1)
        counter += 1

    # For each of these days, get the production metric.
    production_metrics = []
    for day in dates_list:
        production_metrics.append(get_quota_done_helper(day, owner))

    return HTMLResponse(
        content=str(sum(production_metrics)),
        status_code=200
    )

class clearbp_data(BaseModel):
    date: str

@router.post("/api/bps/clear")
async def clear_bp(request: Request, data: clearbp_data, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is clearing the battleplan for {data.date}.")
    date = datetime.datetime.strptime(data.date, "%d-%B-%Y")
    bp_exists = get_bp_exists(date, owner)
    if not bp_exists:
        return JSONResponse(content={"success": False, "error": "Battleplan does not exist."}, status_code=404)
    else:
        # Delete all tasks and quotas on that date,
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM bp_tasks WHERE date = ? and owner = ?",
                    (date.strftime("%d-%m-%Y"), owner,)
                )
                cursor.execute(
                    "DELETE FROM bp_quotas WHERE date = ? and owner = ?",
                    (date.strftime("%d-%m-%Y"), owner,)
                )
                cursor.execute(
                    "DELETE FROM bp_quotas_done WHERE date = ? and owner = ?",
                    (date.strftime("%d-%m-%Y"), owner,)
                )
                conn.commit()
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while clearing a battleplan: {err}", exception=err)
                conn.rollback()
                return JSONResponse(
                    content={
                        "success": False,
                        "error": "Database error occurred while clearing a battleplan."
                    },
                    status_code=500
                )

class yesterday_import_bp_data(BaseModel):
    date_today: str

@router.post("/api/bps/yesterday_import")
async def yesterday_import(request: Request, data: yesterday_import_bp_data, token: str = Depends(require_valid_token)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is importing yesterday's battleplan to {data.date_today}.")

    date_today = datetime.datetime.strptime(data.date_today, "%d-%B-%Y")
    t_bp_exists = get_bp_exists(date_today, owner)
    if not t_bp_exists:
        return JSONResponse(content={"success": False, "error": "Battleplan for today does not exist."}, status_code=409)

    date_yesterday = date_today - datetime.timedelta(days=1)
    y_bp_exists = get_bp_exists(date_yesterday, owner)
    if not y_bp_exists:
        return JSONResponse(content={"success": False, "error": "Battleplan does not exist."}, status_code=404)

    # Get yesterday's tasks and quotas.
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT task_id, date, task, is_done, owner FROM bp_tasks WHERE date = ? AND owner = ? AND is_done = ?",
                (date_yesterday.strftime("%d-%m-%Y"), owner, False)
            )
            tasks = cursor.fetchall()
            if not tasks:
                tasks = [(None, None, None, None, None)]
            cursor.execute(
                "SELECT date, amount, owner FROM bp_quotas WHERE date = ? AND owner = ?",
                (date_yesterday.strftime("%d-%m-%Y"), owner)
            )
            quotas = cursor.fetchone()
            if not quotas:
                quotas = (date_yesterday, 0, owner)
            cursor.execute(
                "SELECT date, amount_done, owner FROM bp_quotas_done WHERE date = ? AND owner = ?",
                (date_yesterday.strftime("%d-%m-%Y"), owner)
            )
            quotas_done = cursor.fetchone()
            if not quotas_done:
                quotas_done = (date_yesterday, 0, owner)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while importing yesterday's battleplan: {err}", exception=err)
            conn.rollback()
            return JSONResponse(
                content={
                    "success": False,
                    "error": "Database error occurred while importing yesterday's battleplan during the get phase."
                },
                status_code=500
            )

        try:
            cursor = conn.cursor()
            for task in tasks:
                cursor.execute(
                    "INSERT INTO bp_tasks (date, task, is_done, owner) VALUES (?, ?, ?, ?)",
                    (date_today.strftime("%d-%m-%Y"), task[2], task[3], owner)
                )
            try:
                cursor.execute(
                    "INSERT INTO bp_quotas (date, amount, owner) VALUES (?, ?, ?)",
                    (date_today.strftime("%d-%m-%Y"), quotas[1], owner)
                )
            except sqlite3.IntegrityError:
                cursor.execute(
                    "UPDATE bp_quotas SET amount = ? WHERE date = ? AND owner = ?",
                    (quotas[1], date_today.strftime("%d-%m-%Y"), owner)
                )
            try:
                cursor.execute(
                    "INSERT INTO bp_quotas_done (date, amount_done, owner) VALUES (?, ?, ?)",
                    (date_today.strftime("%d-%m-%Y"), quotas_done[1], owner)
                )
            except sqlite3.IntegrityError:
                cursor.execute(
                    "UPDATE bp_quotas_done SET amount_done = ? WHERE date = ? AND owner = ?",
                    (quotas_done[1], date_today.strftime("%d-%m-%Y"), owner)
                )

            conn.commit()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while importing yesterday's battleplan: {err}", exception=err)
            conn.rollback()
            return JSONResponse(
                content={
                    "success": False,
                    "error": "Database error occurred while importing yesterday's battleplan during the insert phase."
                },
                status_code=500
            )

    return JSONResponse(content={"success": True}, status_code=200)