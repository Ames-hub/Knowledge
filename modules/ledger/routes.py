from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.auth import require_valid_token
from fastapi.responses import HTMLResponse
from library.logbook import LogBookHandler
from fastapi.responses import JSONResponse
from library.database import DB_PATH
from library.auth import authbook
from pydantic import BaseModel
import sqlite3
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("Finance Records")

@router.get("/ledger", response_class=HTMLResponse)
async def show_home(request: Request, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the ledger.")
    return templates.TemplateResponse(
        request,
        "ledger.html",
    )

@router.get("/api/finances/load_accounts")
async def load_accounts():
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT account_id, account_name, balance FROM finance_accounts"
            )
            data = cursor.fetchall()

            parsed_data = []
            for item in data:
                parsed_data.append({
                    "account_id": item[0],
                    "account_name": item[1],
                    "balance": item[2]
                })
            return parsed_data
        except sqlite3.OperationalError:
            conn.rollback()
            return None

@router.get("/api/finances/load_transactions/{account_id}")
async def load_transactions(account_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT transaction_id, account_id, amount, is_expense, description, date, time
                FROM finance_transactions
                WHERE account_id = ?
                ORDER BY date DESC, time DESC
                """,
                (account_id,)
            )
            data = cursor.fetchall()
            parsed_data = []
            for item in data:
                parsed_data.append({
                    "transaction_id": item[0],
                    "account_id": item[1],
                    "amount": item[2],
                    "is_expense": item[3],
                    "description": item[4],
                    "date": item[5],
                    "time": item[6]
                })
            return JSONResponse(parsed_data, status_code=200)
        except sqlite3.OperationalError:
            conn.rollback()
            return JSONResponse(content={"error": "Database error occurred while fetching transactions."}, status_code=500)

class finances_data(BaseModel):
    account_id: int
    amount: float
    description: str
    is_expense: bool

@router.post("/api/finances/modify", response_class=JSONResponse)
async def modify_finances(request: Request, data: finances_data, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has modified finances.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO finance_transactions (account_id, amount, is_expense, description)
                VALUES (?, ?, ?, ?)
                """,
                (data.account_id, data.amount, data.is_expense, data.description)
            )
            cur.execute(
                f"""
                UPDATE finance_accounts SET balance = balance {"+" if not data.is_expense else "-"} ? WHERE account_id = ?
                """,
                (data.amount, data.account_id)
            )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError:
            conn.rollback()
            return JSONResponse(
                content={"success": False, "error": "Database error occurred while modifying finances."},
                status_code=500
            )

class make_account_data(BaseModel):
    account_name: str

@router.post("/api/finances/account/make", response_class=JSONResponse)
async def make_account(request: Request, data: make_account_data, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has made a new finance account under the name {data.account_name}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO finance_accounts (account_name) VALUES (?)",
                (data.account_name,)
            )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError:
            conn.rollback()
            return JSONResponse(content={"success": False, "error": "Database error occurred while making the account."}, status_code=500)

class del_account_data(BaseModel):
    account_id: int

@router.post("/api/finances/account/delete", response_class=JSONResponse)
async def del_account(request: Request, data: del_account_data, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has deleted the finance account with the ID {data.account_id}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM finance_accounts WHERE account_id = ?",
                (data.account_id,)
            )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError:
            conn.rollback()
            return JSONResponse(content={"success": False, "error": "Database error occurred while deleting the account."}, status_code=500)