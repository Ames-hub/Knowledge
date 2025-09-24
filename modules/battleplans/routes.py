from fastapi.responses import HTMLResponse, JSONResponse
from library.auth import authbook, require_prechecks
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.authperms import set_permission
from library.logbook import LogBookHandler
from library.database import DB_PATH
from pydantic import BaseModel
from library import settings
import datetime
import sqlite3
import os

logbook = LogBookHandler("BattlePlans")
router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

def get_bp_exists(date: datetime.datetime, owner: str):
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM battleplans WHERE date = ? AND owner = ?",
                (date.strftime("%d-%m-%Y"), owner)
            )
            data = cursor.fetchone()
            return bool(data[0]) if data else False
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while checking if a battleplan exists: {err}", exception=err)
            return False

def get_bp_id(date: datetime.datetime, owner: str):
    """Fetch the bp_id for a given date and owner."""
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT bp_id FROM battleplans WHERE date = ? AND owner = ?",
                (date.strftime("%d-%m-%Y"), owner)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error getting bp_id for {date}: {err}", exception=err)
            return None

def dateformatenforcer(date: str):
    date = date.lower()
    if len(date) > 10:  # likely month name
        month_list = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12",
        }
        for month in month_list.keys():
            if month in date:
                date = date.replace(month, str(month_list[month]))
    return date

def get_quota_done_helper(date: str, owner: str):
    date = dateformatenforcer(date)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT done_amount, name, bp_id
                FROM bp_quotas
                WHERE bp_date = ? AND owner = ?
                """,
                (date, owner),
            )
            data = cursor.fetchall()

            prod_data = {}
            for done_amount, name, bp_id in data:
                if bp_id not in prod_data:
                    prod_data[bp_id] = {}
                if name not in prod_data[bp_id]:
                    prod_data[bp_id][name] = []
                prod_data[bp_id][name].append(done_amount)

            return prod_data

        except sqlite3.OperationalError as err:
            logbook.error(
                f"Database error occurred while fetching the quota amount: {err}",
                exception=err,
            )
            conn.rollback()
            return {}

# -------------------- Routes --------------------

@router.get("/battleplans", response_class=HTMLResponse)
@set_permission(permission="battleplans")
async def show_login(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) has accessed the battleplans page.")
    return templates.TemplateResponse(request, "battleplans.html")

@router.get("/api/bps/list", response_class=JSONResponse)
async def list_bps(request: Request, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is listing all battleplans.")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT date FROM battleplans WHERE owner = ?", (owner,))
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

@router.get("/api/bps/get/{date}", response_class=JSONResponse)
async def get_bp(request: Request, date: str, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is fetching all tasks for {date}.")
    date_obj = datetime.datetime.strptime(date, "%d-%B-%Y")

    if not get_bp_exists(date_obj, owner):
        return JSONResponse({"success": False, "error": "Battleplan does not exist."}, status_code=404)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT date, task, is_done, task_id, category FROM bp_tasks WHERE date = ? and owner = ?",
            (date_obj.strftime("%d-%m-%Y"), owner,)
        )
        data = cursor.fetchall()

    bp_id = get_bp_id(date_obj, owner)

    parsed_data = {"bp_id": bp_id, "date": date_obj.strftime("%d-%m-%Y"), "tasks": []}
    for item in data:
        parsed_data["tasks"].append({"text": item[1], "done": bool(item[2]), "id": item[3], "category": item[4]})

    return JSONResponse(parsed_data, status_code=200)

class task_state_data(BaseModel):
    task_id: str
    state: bool

@router.get("/api/bps/task/delete/{task_id}")
async def delete_task(request: Request, task_id: str, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is deleting task {task_id}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bp_tasks WHERE task_id = ?", (int(task_id),))
            conn.commit()
            return JSONResponse({"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while deleting task: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while deleting task."}, status_code=500)

@router.post("/api/bps/task/set_status", response_class=JSONResponse)
async def set_task_status(request: Request, data: task_state_data, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is setting status of task {data.task_id} to {data.state}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE bp_tasks SET is_done = ? WHERE task_id = ?", (bool(data.state), int(data.task_id)))
            conn.commit()
            return JSONResponse({"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while setting task status: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while setting task status."}, status_code=500)

@router.get("/api/bps/create/{date}")
async def create_bp(request: Request, date: str, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is creating battleplan for {date}.")
    date_obj = datetime.datetime.strptime(date, "%d-%B-%Y")

    if get_bp_exists(date_obj, owner):
        return JSONResponse({"success": False, "error": "Battleplan already exists."}, status_code=409)

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO battleplans (date, owner) VALUES (?, ?)", (date_obj.strftime("%d-%m-%Y"), owner))
            conn.commit()
            return JSONResponse({"success": True}, status_code=201)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while creating battleplan: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while creating battleplan."}, status_code=500)

class add_task_data(BaseModel):
    text: str
    date: str
    category: str

@router.post("/api/bps/task/add")
async def add_task(request: Request, data: add_task_data, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is adding task to battleplan for {data.date}.")
    data.date = dateformatenforcer(data.date)
    date_obj = datetime.datetime.strptime(data.date, "%d-%m-%Y")

    if not get_bp_exists(date_obj, owner):
        return JSONResponse({"success": False, "error": "Battleplan does not exist."}, status_code=404)

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO bp_tasks (date, task, is_done, owner, category) VALUES (?, ?, ?, ?, ?)",
                (date_obj.strftime("%d-%m-%Y"), str(data.text), False, owner, str(data.category))
            )
            conn.commit()
            return JSONResponse({"id": cursor.lastrowid, "text": data.text, "done": False}, status_code=201)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while adding task: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while adding task."}, status_code=500)

# -------------------- Quota Endpoints --------------------

class quota_data_set(BaseModel):
    quota_id: int
    amount: float|int

class quota_data_get(BaseModel):
    name: str
    date: str

class quota_make(BaseModel):
    bp_id: int
    quota_name: str

class quota_delete(BaseModel):
    quota_id: int

@router.post("/api/bps/quota/delete")
async def delete_quota(request: Request, data: quota_delete, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is deleting the quota {data.quota_id}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM bp_quotas WHERE quota_id = ? AND owner = ?
                """,
                (data.quota_id, owner,)
            )
            conn.commit()
            return JSONResponse({"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while deleting quota: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while deleting quota."}, status_code=500)

def check_quota_exists(bp_id: int, quota_name: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM bp_quotas WHERE name = ? AND bp_id = ?
                """,
                (quota_name, bp_id,)
            )
            data = cursor.fetchone()
            return True if data is not None else False
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while checking quota: {err}", exception=err)
            return False

@router.post("/api/bps/quota/create")
async def create_quota(request: Request, data: quota_make, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is creating the quota {data.quota_name} for BP with ID {data.bp_id}.")

    with sqlite3.connect(DB_PATH) as conn:
        try:
            # Check if the quota already exists
            if check_quota_exists(data.bp_id, data.quota_name):
                return JSONResponse(
                    content={"success": False, "error": "Quota already exists."},
                    status_code=409
                )

            cursor = conn.cursor()
            cursor.execute(
                "SELECT date FROM battleplans WHERE bp_id = ? AND owner = ?",
                (data.bp_id, owner,)
            )
            bp_date = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO bp_quotas
                (bp_id, bp_date, planned_amount, done_amount, owner, name)
                VALUES (?, ?, ?, ?, ? , ?)
                """,
                (data.bp_id, bp_date, 0, 0, owner, data.quota_name))
            conn.commit()
            return JSONResponse({"success": True}, status_code=201)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while creating quota: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while creating quota."}, status_code=500)

@router.get("/api/bps/quota/list/{bp_date}")
async def list_quotas(request: Request, bp_date:str, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    bp_date = dateformatenforcer(bp_date)
    logbook.info(f"IP {request.client.host} ({owner}) is listing all quotas for {bp_date}.")

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                    SELECT quota_id, bp_id, bp_date, planned_amount, done_amount, owner, name
                    FROM bp_quotas
                    WHERE owner = ? AND bp_date = ?  -- Its quota's by BP Date and Owner. Not every BP has the same quota's
                """,
                (owner, bp_date)
            )
            data = cursor.fetchall()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while listing quotas: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while fetching quotas."}, status_code=500)

    parsed_data = []
    for item in data:
        parsed_data.append({
            "quota_id": item[0],
            "bp_id": item[1],
            "date": item[2],
            "planned_amount": item[3],
            "done_amount": item[4],
            "owner": item[5],
            "name": item[6]
        })
    return JSONResponse(parsed_data, status_code=200)

@router.post("/api/bps/quota/done/set")
async def set_quota_done(request: Request, data: quota_data_set, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is setting quota done amount for quota {data.quota_id} to {data.amount}.")

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE bp_quotas SET done_amount = ? WHERE quota_id = ? AND owner = ?",
                (data.amount, data.quota_id, owner)
            )
            conn.commit()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while setting quota done amount: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while setting done quota amount."}, status_code=500)

@router.post("/api/bps/quota/wanted/set")
async def set_quota_wanted(request: Request, data: quota_data_set, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is setting the wanted quota amount for quota {data.quota_id} to {data.amount}.")

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE bp_quotas SET planned_amount = ? WHERE quota_id = ? AND owner = ?",
                (data.amount, data.quota_id, owner)
            )
            conn.commit()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while setting wanted quota amount: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while setting wanted quota amount."}, status_code=500)

class weekly_prod_get(BaseModel):
    date: str

@router.post("/api/bps/quota/weekly")
async def get_weekly_production(request: Request, data: weekly_prod_get, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is fetching weekly production for {data.date}.")

    # Ensure date format
    date_str = dateformatenforcer(data.date)
    try:
        date_obj = datetime.datetime.strptime(date_str, "%d-%m-%Y").date()
    except ValueError:
        return HTMLResponse("Invalid date format. Use DD-MM-YYYY.", status_code=400)

    week_start = settings.get.get_week_end()
    if week_start < 1 or week_start > 7:
        return HTMLResponse("week_start must be 1 (Monday) to 7 (Sunday).", status_code=400)

    # Calculate the difference to move to the start of the week
    current_weekday = date_obj.isoweekday()  # 1=Monday, 7=Sunday
    delta_days = (current_weekday - week_start) % 7
    start_of_week = date_obj - datetime.timedelta(days=delta_days)

    # Build the 7-day week list from the start
    dates_list = [(start_of_week + datetime.timedelta(days=i)).strftime("%d-%m-%Y") for i in range(7)]

    # Gather and merge production data
    weekly_data = {}
    for day in dates_list:
        day_data = get_quota_done_helper(day, owner)
        for bp_id, names in day_data.items():
            if bp_id not in weekly_data:
                weekly_data[bp_id] = {}
            for name, amounts in names.items():
                if name not in weekly_data[bp_id]:
                    weekly_data[bp_id][name] = []
                weekly_data[bp_id][name].extend(amounts)

    # Optionally calculate totals
    weekly_totals = {}
    for bp_id, names in weekly_data.items():
        weekly_totals[bp_id] = {}
        for name, amounts in names.items():
            weekly_totals[bp_id][name] = sum(amounts)

    return JSONResponse({"weekly_data": weekly_data, "weekly_totals": weekly_totals})

class clearbp_data(BaseModel):
    date: str

@router.post("/api/bps/clear")
async def clear_bp(request: Request, data: clearbp_data, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is clearing battleplan for {data.date}.")
    date_obj = datetime.datetime.strptime(data.date, "%d-%B-%Y")

    if not get_bp_exists(date_obj, owner):
        return JSONResponse({"success": False, "error": "Battleplan does not exist."}, status_code=404)

    bp_id = get_bp_id(date_obj, owner)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bp_tasks WHERE date = ? AND owner = ?", (date_obj.strftime("%d-%m-%Y"), owner))
            cursor.execute("DELETE FROM bp_quotas WHERE bp_id = ? AND owner = ?", (bp_id, owner))
            conn.commit()
            return JSONResponse({"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while clearing battleplan: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while clearing battleplan."}, status_code=500)

class yesterday_import_bp_data(BaseModel):
    date_today: str

@router.post("/api/bps/yesterday_import")
async def yesterday_import(request: Request, data: yesterday_import_bp_data, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({owner}) is importing yesterday's battleplan to {data.date_today}.")

    date_today = datetime.datetime.strptime(data.date_today, "%d-%B-%Y")
    if not get_bp_exists(date_today, owner):
        return JSONResponse({"success": False, "error": "Battleplan for today does not exist."}, status_code=409)

    date_yesterday = date_today - datetime.timedelta(days=1)
    if not get_bp_exists(date_yesterday, owner):
        return JSONResponse({"success": False, "error": "A Battleplan for Yesterday does not exist."}, status_code=404)

    today_bp_id = get_bp_id(date_today, owner)
    yesterday_bp_id = get_bp_id(date_yesterday, owner)

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()

            # Fetch yesterday's tasks
            cursor.execute(
                "SELECT task_id, task, is_done FROM bp_tasks WHERE date = ? AND owner = ? AND is_done = ?",
                (date_yesterday.strftime("%d-%m-%Y"), owner, False)
            )
            task_data = cursor.fetchall()

            # Fetch yesterday's quotas
            cursor.execute(
                "SELECT bp_id, bp_date, planned_amount, done_amount, owner, name FROM bp_quotas WHERE bp_id = ? AND owner = ?",
                (yesterday_bp_id, owner)
            )
            quota_row = cursor.fetchall()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error during yesterday's import (fetch): {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error during yesterday's import."}, status_code=500)

        tasks = []
        for task in task_data:
            tasks.append({
                "task_id": task[0],
                "task": task[1],
                "is_done": task[2]
            })
        quotas_list = []
        for item in quota_row:
            # Only append non-existent quotas
            quota_exists = check_quota_exists(today_bp_id, item[5])
            if not quota_exists:
                quotas_list.append({
                    "bp_id": item[0],
                    "bp_date": item[1],
                    "planned_amount": item[2],
                    "done_amount": item[3],
                    "owner": item[4],
                    "name": item[5]
                })
            else:
                logbook.info(f"The quota name {item[5]} for BP ID {today_bp_id} does exists. Skipping.")

        try:
            # Insert tasks for today
            for task in tasks:
                cursor.execute(
                    "INSERT INTO bp_tasks (date, task, is_done, owner) VALUES (?, ?, ?, ?)",
                    (date_today.strftime("%d-%m-%Y"), task['task'], task['is_done'], owner)
                )

            # Insert or update quota
            for quota in quotas_list:
                planned_amount = quota['planned_amount']
                # If yesterday is the day of the end of the week, set 'planned_amount' to 0 for the day of the new week.
                if date_today.isoweekday() - 1 == settings.get.get_week_end():
                    if settings.get.reset_bp_plan_on_new_week():
                        planned_amount = 0

                try:
                    cursor.execute(
                        "INSERT INTO bp_quotas (bp_id, bp_date, planned_amount, done_amount, owner, name) VALUES (?, ?, ?, ?, ?, ?)",
                        (today_bp_id, date_today.strftime("%d-%m-%Y"), planned_amount, 0, quota['owner'], quota['name'])
                    )
                except sqlite3.IntegrityError:
                    cursor.execute(
                        "UPDATE bp_quotas SET bp_id = ?, bp_date = ?, planned_amount = ?, done_amount = ?, owner = ?, name = ? WHERE bp_id = ? AND owner = ?",
                        (today_bp_id, date_today.strftime("%d-%m-%Y"), planned_amount, 0, quota['owner'], quota['name'])
                    )

            conn.commit()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error during yesterday's import (insert): {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error during yesterday's import insert phase."}, status_code=500)

    return JSONResponse({"success": True}, status_code=200)