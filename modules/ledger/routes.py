from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.authperms import set_permission
from library.auth import require_prechecks
from library.logbook import LogBookHandler
from library.database import DB_PATH
from library.auth import authbook
from pydantic import BaseModel
import sqlite3
import datetime
import magic
import os
import io

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("Finance Records")

@router.get("/ledger", response_class=HTMLResponse)
@set_permission(permission="ledger")
async def show_home(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the ledger.")
    return templates.TemplateResponse(
        request,
        "ledger.html",
    )

@router.get("/api/finances/load_accounts")
async def load_accounts(request: Request, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} (user: {owner}) is loading finance accounts.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT account_id, account_name, balance FROM finance_accounts",
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

@router.get("/api/finances/account/total_expenses/{account_id}")
async def get_total_expenses(request: Request, account_id:int, token: str = Depends(require_prechecks)):
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) has accessed total expenses for account {account_id}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT SUM(amount) FROM finance_transactions WHERE is_expense = true AND account_id = ?",
                (account_id,)
            )
            data = cursor.fetchone()
            try:
                amount = data[0]
            except TypeError:
                amount = None
            if amount is None:
                return 0
            return HTMLResponse(f"{data[0]}", status_code=200)
        except sqlite3.OperationalError:
            conn.rollback()
            return None

@router.get("/api/finances/account/total_income/{account_id}")
async def get_total_expenses(account_id:int):
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT SUM(amount) FROM finance_transactions WHERE is_expense = false AND account_id = ?",
                (account_id,)
            )
            data = cursor.fetchone()
            try:
                amount = data[0]
            except TypeError:
                amount = None
            if amount is None:
                return 0

            amount = data[0]
            # Round-down the decimal points to 2
            amount = round(amount, 2)
            return HTMLResponse(f"{amount}", status_code=200)
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
    receipt_bytes: list = None

@router.post("/api/finances/modify", response_class=JSONResponse)
async def modify_finances(request: Request, data: finances_data, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has modified finances.")

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()

            # Insert transaction
            cur.execute(
                """
                INSERT INTO finance_transactions (account_id, amount, is_expense, description)
                VALUES (?, ?, ?, ?)
                """,
                (data.account_id, data.amount, data.is_expense, data.description)
            )

            # Update account balance
            cur.execute(
                f"""
                UPDATE finance_accounts SET balance = balance {"+" if not data.is_expense else "-"} ? WHERE account_id = ?
                """,
                (data.amount, data.account_id)
            )

            # Add the receipt if it exists
            if data.receipt_bytes:
                transaction_id = cur.lastrowid
                receipt_bytes = bytes(data.receipt_bytes)

                # Detect MIME type from the actual bytes
                mime = magic.Magic(mime=True)
                receipt_type = mime.from_buffer(receipt_bytes) or "application/octet-stream"

                cur.execute(
                    """
                    INSERT INTO transaction_receipts (transaction_id, receipt, receipt_mimetype)
                    VALUES (?, ?, ?)
                    """,
                    (transaction_id, receipt_bytes, receipt_type)
                )

            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)

        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while modifying finances: {err}", exception=err)
            conn.rollback()
            return JSONResponse(
                content={"success": False, "error": "Database error occurred while modifying finances."},
                status_code=500
            )

@router.get("/api/finances/get_receipt/{transaction_id}")
async def get_receipt(transaction_id: int):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT receipt FROM transaction_receipts WHERE transaction_id = ?",
                (transaction_id,)
            )
            data = cursor.fetchone()

            if data is None or data[0] is None:
                return JSONResponse(
                    content={"error": "Receipt not found."},
                    status_code=404
                )

            receipt_bytes = data[0]
            return StreamingResponse(io.BytesIO(receipt_bytes), media_type="image/png")
    except sqlite3.OperationalError:
        return JSONResponse(
            content={"error": "Database error occurred while fetching receipt."},
            status_code=500
        )

@router.get("/api/transactions/get_receipt_mime/{transaction_id}")
async def get_receipt_mime(transaction_id: int):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT receipt_mimetype FROM transaction_receipts WHERE transaction_id = ?",
                (transaction_id,)
            )
            data = cursor.fetchone()
            if data is None or data[0] is None:
                return HTMLResponse(
                    content="",  # It can handle this
                    status_code=404
                )
            return HTMLResponse(
                data[0],
                status_code=200
            )
    except sqlite3.OperationalError:
        return HTMLResponse(
            "",  # It can handle this
            status_code=500
        )

class transaction_delete(BaseModel):
    transaction_id: int

@router.post("/api/finances/del_transaction", response_class=JSONResponse)
async def del_transaction(request: Request, data: transaction_delete, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has deleted a finance transaction.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT amount, is_expense, account_id FROM finance_transactions WHERE transaction_id = ?",
                (data.transaction_id,)
            )
            db_data = cursor.fetchone()
            amount = db_data[0]
            is_expense = bool(db_data[1])
            account_id = db_data[2]

            # Update account balance
            cursor.execute(
                f"""
                UPDATE finance_accounts SET balance = balance {"+" if is_expense else "-"} ?
                WHERE account_id = ?
                """,
                (amount, account_id)
            )

            cursor.execute(
                "DELETE FROM finance_transactions WHERE transaction_id = ?",
                (data.transaction_id,)
            )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError:
            conn.rollback()
            return JSONResponse(content={"success": False, "error": "Database error occurred while deleting the transaction."}, status_code=500)

class make_account_data(BaseModel):
    account_name: str

@router.post("/api/finances/account/make", response_class=JSONResponse)
async def make_account(request: Request, data: make_account_data, token: str = Depends(require_prechecks)):
    username = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} (user: {username}) has made a new finance account under the name {data.account_name}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO finance_accounts (account_name, owner) VALUES (?, ?)",
                (data.account_name, username)
            )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError:
            conn.rollback()
            return JSONResponse(content={"success": False, "error": "Database error occurred while making the account."}, status_code=500)

class del_account_data(BaseModel):
    account_id: int

@router.post("/api/finances/account/delete", response_class=JSONResponse)
async def del_account(request: Request, data: del_account_data, token: str = Depends(require_prechecks)):
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

@router.get("/ledger/planning")
@set_permission(permission="ledger")
async def planning(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the financial planning page.")
    return templates.TemplateResponse(
        request,
        "planning.html",
    )

class expense_data(BaseModel):
    name: str
    amount: float
    frequency: int
    annualCost: float

@router.post("/api/finances/fp/add_expense")
async def add_fp_expense(request: Request, data: expense_data, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has added an expense to the FP No. 1.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO fp_expenses (name, amount, frequency, annual_cost) VALUES (?, ?, ?, ?)",
                (data.name, data.amount, data.frequency, data.annualCost)
            )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError:
            conn.rollback()
            return JSONResponse(content={"success": False, "error": "Database error occurred while adding the expense."}, status_code=500)

class del_expense_data(BaseModel):
    name: str

@router.post("/api/finances/fp/delete_expense")
async def delete_fp_expense(request: Request, data: del_expense_data, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has deleted an expense from the FP No. 1.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM fp_expenses WHERE name = ?",
                (data.name,)
            )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError:
            conn.rollback()
            return JSONResponse(content={"success": False, "error": "Database error occurred while deleting the expense."}, status_code=500)

@router.get("/api/finances/fp/get_expenses")
async def get_fp_expenses(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the FP No. 1.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, amount, frequency, annual_cost FROM fp_expenses"
            )
            data = cursor.fetchall()
            parsed_data = []
            for item in data:
                parsed_data.append({
                    "name": item[0],
                    "amount": item[1],
                    "frequency": item[2],
                    "annual_cost": item[3]
                })
            return JSONResponse(parsed_data, status_code=200)
        except sqlite3.OperationalError:
            conn.rollback()
            return JSONResponse(content={"error": "Database error occurred while fetching expenses."}, status_code=500)

@router.get("/ledger/debts")
@set_permission(permission="ledger")
async def debts_page(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the debts record page.")
    return templates.TemplateResponse(
        request,
        "debts.html",
    )

class debts:
    @staticmethod
    def check_exists(debt_id):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT debt_id FROM debts WHERE debt_id = ?",
                    (debt_id,)
                )
                data = cursor.fetchone()
                if data is None:
                    return False
                else:
                    return True
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while checking if a debt exists: {err}", exception=err)
                conn.rollback()
                return False

    @staticmethod
    def get_all_debts():
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT debt_id, debtor, debtee, amount, start_date, end_date FROM debts"
                )
                data = cursor.fetchall()
                parsed_data = {}
                for item in data:
                    if "." in item[4]:  # TODO: Figure out what gives this string the .%f
                        start_datetime_obj = datetime.datetime.strptime(item[4], "%Y-%m-%d %H:%M:%S.%f")
                    else:
                        start_datetime_obj = datetime.datetime.strptime(item[4], "%Y-%m-%d %H:%M:%S")
                    if item[5] is not None:
                        if "." in item[5]:
                            end_datetime_obj = datetime.datetime.strptime(item[5], "%Y-%m-%d %H:%M:%S.%f")
                        else:
                            end_datetime_obj = datetime.datetime.strptime(item[5], "%Y-%m-%d %H:%M:%S")
                        end_value = end_datetime_obj.strftime("%Y-%m-%d")
                    else:
                        end_value = None
                    parsed_data[item[0]] = {
                        "debt_id": item[0],
                        "debtor": item[1],
                        "debtee": item[2],
                        "amount": item[3],
                        "start_date": start_datetime_obj.strftime("%Y-%m-%d"),
                        "end_date": end_value,
                    }
                return parsed_data
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while fetching all debts: {err}", exception=err)
                conn.rollback()
                return None

    @staticmethod
    def get_debt_data(debt_id):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT debt_id, debtor, debtee, amount, start_date, end_date FROM debts WHERE debt_id = ?",
                    (debt_id,)
                )
                data = cursor.fetchone()
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while fetching debt data: {err}", exception=err)
                conn.rollback()
                return None

        if data is None:
            return None

        if "." in data[4]:  # TODO: Figure out what gives this string the .%f
            start_datetime_obj = datetime.datetime.strptime(data[4], "%Y-%m-%d %H:%M:%S.%f")
        else:
            start_datetime_obj = datetime.datetime.strptime(data[4], "%Y-%m-%d %H:%M:%S")
        if data[5] is not None:
            if "." in data[5]:
                end_datetime_obj = datetime.datetime.strptime(data[5], "%Y-%m-%d %H:%M:%S")
            else:
                end_datetime_obj = datetime.datetime.strptime(data[5], "%Y-%m-%d %H:%M:%S")
            end_value = end_datetime_obj.strftime("%Y-%m-%d")
        else:
            end_value = None
        return {
            "debt_id": data[0],
            "debtor": data[1],
            "debtee": data[2],
            "amount": data[3],
            "start_date": start_datetime_obj.strftime("%Y-%m-%d"),
            "end_date": end_value,
        }

    @staticmethod
    def delete_debt(debt_id):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM debts WHERE debt_id = ?",
                    (debt_id,)
                )
                conn.commit()
                return True
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while deleting a debt: {err}", exception=err)
                conn.rollback()
                return False

    @staticmethod
    def create_new_debt(debtor:str, debtee:str, amount:float, description:str, start_date=None, end_date=None, cfid=None):
        if not start_date:
            start_date = datetime.datetime.now()
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO debts (debtor, debtee, amount, start_date, end_date, cfid)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (debtor, debtee, amount, start_date, end_date, cfid)
                )
                debt_id = cursor.lastrowid
                cursor.execute(
                    """
                    INSERT INTO debt_records (debt_id, amount, description, start_date, paid_off)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (debt_id, amount, description, start_date, False)
                )
                conn.commit()
                return debt_id
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while creating a new debt: {err}", exception=err)
                conn.rollback()
                return False

    @staticmethod
    def record_new_debt_instance(debt_id, amount, description, start_date=None):
        if not start_date:
            start_date = datetime.datetime.now()
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE debts SET amount = amount + ? WHERE debt_id = ?
                    """,
                    (int(amount), int(debt_id))
                )
                cursor.execute(
                    """
                    INSERT INTO debt_records (debt_id, amount, description, start_date, paid_off)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (debt_id, amount, description, start_date, False)
                )
                conn.commit()
                return cursor.lastrowid  # The record_id
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while recording a new debt instance: {err}", exception=err)
                conn.rollback()
                return False

    @staticmethod
    def get_record_amount(record_id):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT amount FROM debt_records WHERE record_id = ?",
                    (record_id,)
                )
                data = cursor.fetchone()
                if data is None:
                    return None
                else:
                    return data[0]
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while fetching a debt record amount: {err}", exception=err)
                conn.rollback()
                return False

    @staticmethod
    def subtract_debt(debt_id, amount, record_id):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE debts SET amount = amount - ? WHERE debt_id = ?
                    """,
                    (int(amount), int(debt_id))
                )
                if debts.get_record_amount(record_id) - amount > 0:  # Not enough to pay it off 100%
                    cur.execute(
                        """
                        UPDATE debt_records SET amount = amount - ? WHERE record_id = ?
                        """,
                        (int(amount), int(debt_id))
                    )
                else:  # Paid off
                    cur.execute(
                        """
                        UPDATE debt_records SET amount = 0 AND paid_off = True WHERE record_id = ?
                        """,
                        (int(record_id),)
                    )
                conn.commit()
                return True
            except sqlite3.OperationalError as err:
                logbook.error(
                    message=f"Database error occurred while subtracting {amount} in debt for record {record_id} and debt {debt_id}: {err}",
                    exception=err
                )
                conn.rollback()
                return False

    @staticmethod
    def find_debt_id(debtor, debtee):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT debt_id FROM debts WHERE debtor = ? AND debtee = ?",
                    (debtor, debtee)
                )
                data = cursor.fetchone()
                if data is None:
                    return None
                else:
                    return data[0]
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while finding a debt ID: {err}", exception=err)
                conn.rollback()
                return None

    @staticmethod
    def get_debt_records(debt_id):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT record_id, debt_id, amount, description, start_date, paid_off FROM debt_records WHERE debt_id = ? AND paid_off = False",
                    (debt_id,)
                )
                data = cursor.fetchall()
                parsed_data = {}
                for item in data:
                    datetime_obj = datetime.datetime.strptime(item[4], "%Y-%m-%d %H:%M:%S.%f")
                    parsed_data[item[0]] = {
                        "record_id": item[0],
                        "debt_id": item[1],
                        "amount": item[2],
                        "description": item[3],
                        "start_date": datetime_obj.strftime("%Y-%m-%d"),
                        "paid_off": bool(item[5]),
                    }
                return parsed_data
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while fetching debt records: {err}", exception=err)
                conn.rollback()
                return None

class debt_data(BaseModel):
    debtor: str
    debtee: str
    amount: float
    description: str
    start_date: str | None = None
    due_date: str | None = None
    cfid: int|str|None

@router.post("/api/finances/debts/add")
@set_permission(permission="ledger")
async def add_debt(request: Request, data: debt_data, token: str = Depends(require_prechecks)):
    debt_id = debts.find_debt_id(data.debtor, data.debtee)
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has added a debt of {data.amount} from the debt with the ID {debt_id}.")

    if data.cfid is not None:
        if data.cfid.isnumeric():
            data.cfid = int(data.cfid)
        else:
            data.cfid = None

    due_date = datetime.datetime.now().strptime(data.due_date, "%Y-%m-%d") if data.due_date is not None else None
    start_date = datetime.datetime.now().strptime(data.start_date, "%Y-%m-%d") if data.start_date is not None else None
    description = data.description if data.description is not None else "No description provided."

    try:
        if not debts.check_exists(debt_id):
            debt_id = debts.create_new_debt(
                debtor=data.debtor,
                debtee=data.debtee,
                amount=data.amount,
                start_date=start_date,
                end_date=due_date,
                description=description,
                cfid=data.cfid
            )
            success = True if type(debt_id) is int else False
            return JSONResponse(content={"success": success, "debt_id": debt_id}, status_code=200 if success else 500)
        else:
            record_id = debts.record_new_debt_instance(
                debt_id=debt_id,
                amount=data.amount,
                description=data.description,
                start_date=data.start_date
            )
            success = True if type(record_id) is int else False
            return JSONResponse(content={"success": success, "record_id": record_id}, status_code=200 if success else 500)
    except sqlite3.OperationalError:
        return JSONResponse(content={"success": False, "error": "Database error occurred while adding the debt."}, status_code=500)

class subtract_debt_data(BaseModel):
    debtor: str
    debtee: str
    amount: float
    record_id: int

@router.post("/api/finances/debts/subtract")
async def subtract_debt(request: Request, data: subtract_debt_data, token = Depends(require_prechecks)):
    debt_id = debts.find_debt_id(data.debtor, data.debtee)
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has subtracted {data.amount} from the debt with ID {debt_id}.")
    try:
        debt = debts.get_debt_data(debt_id)
        if debt is None:
            return JSONResponse(content={"success": False, "error": "Debt with the given ID does not exist."}, status_code=404)

        amount = debt['amount']
        if float(amount) - float(data.amount) <= 0:
            success = debts.delete_debt(debt_id)
            if success:
                return JSONResponse(content={"success": success, "action": "Deleted debt as it was 0."}, status_code=200)
            else:
                return JSONResponse(content={"success": False, "error": "Could not delete debt. Server-side error."}, status_code=500)
        else:
            success = debts.subtract_debt(
                debt_id=debt_id,
                amount=data.amount,
                record_id=data.record_id
            )
            return JSONResponse(content={"success": success}, status_code=200 if success else 500)
    except sqlite3.OperationalError:
        return JSONResponse(content={"success": False, "error": "Database error occurred while subtracting the debt."}, status_code=500)

@router.get("/api/finances/debts/get_all")
async def get_debts(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is listing all debts.")
    debt_list = debts.get_all_debts()
    return JSONResponse(debt_list, status_code=200)

class get_records_data(BaseModel):
    debtor: str
    debtee: str

@router.post("/api/finances/debts/get_all_records")
async def get_all_records(request: Request, data: get_records_data, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is listing all debt records.")

    debt_id = debts.find_debt_id(data.debtor, data.debtee)
    if not debt_id:
        return JSONResponse(content={}, status_code=404)
    else:
        records = debts.get_debt_records(debt_id)
        return JSONResponse(records, status_code=200)

# Invoices section

@router.get("/ledger/invoices")
@set_permission(permission="ledger")
async def invoices_page(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the invoices page.")
    return templates.TemplateResponse(
        request,
        "invoices.html",
    )

class get_invoices_data(BaseModel):
    searchTerm: str
    StatusFilter: str

@router.post("/api/ledger/invoices/get-invoices")
async def get_invoice_items(request: Request, data: get_invoices_data, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is listing all invoice items.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            if not data.searchTerm:
                date_search = datetime.datetime.now().strftime("%d-%m-%Y")
            else:
                date_search = data.searchTerm

            is_paid_filter = True if data.StatusFilter.lower() == "paid" else False
            if data.StatusFilter.lower() == "all":
                is_paid_filter = -1

            cursor.execute(
                f"SELECT invoice_id, date, amount, is_paid FROM invoices WHERE date = ? {"AND is_paid = ?" if is_paid_filter != -1 else ""}",
                (date_search, is_paid_filter,) if is_paid_filter != -1 else (date_search,)
            )
            data = cursor.fetchall()

            parsed_data = []
            for item in data:
                parsed_data.append({
                    "id": item[0],
                    "date": item[1],
                    "total": item[2],
                    "paid": bool(item[3]),
                })

            for item in parsed_data:
                invoice_id = item["id"]
                cursor.execute(
                    "SELECT item, value FROM items_on_invoices WHERE invoice_id = ?",
                    (invoice_id,)
                )
                items_data = cursor.fetchall()
                item_list = []
                for item_data in items_data:
                    item_list.append({
                        "item": item_data[0],
                        "value": item_data[1],
                    })
                item["items"] = item_list

            return JSONResponse(parsed_data, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while fetching invoice items: {err}", exception=err)
            conn.rollback()

class del_item_data(BaseModel):
    name: str

@router.post("/api/ledger/invoices/delete-item")
async def delete_item(request: Request, data: del_item_data, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is deleting an invoice item.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM invoice_items WHERE item_id = ?",
                (data.name,)
            )
            conn.commit()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while deleting an invoice item: {err}", exception=err)
            return JSONResponse(content={"success": False, "error": "Database error occurred while deleting an invoice item."}, status_code=500)


class save_invoice_data(BaseModel):
    items: list
    total: float
    cfid: int|None

@router.post("/api/ledger/invoices/save-invoice")
async def save_invoice(request: Request, data: save_invoice_data, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is saving the invoice (invoice  they just made.")
    datenow = datetime.datetime.now().strftime("%d-%m-%Y")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO invoices (date, amount, is_paid, cfid) VALUES (?, ?, ?, ?)
                """,
                (datenow, data.total, False, data.cfid)
            )
            invoice_id = cur.lastrowid
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while saving the invoice: {err}", exception=err)
            conn.rollback()
            return JSONResponse(content={"success": False, "error": "Database error occurred while saving the invoice."}, status_code=500)

        try:
            for item in data.items:
                name, price = item['name'], item['price']
                cur.execute(
                    """
                    INSERT INTO items_on_invoices (invoice_id, item, value) VALUES (?, ?, ?)
                    """,
                    (invoice_id, name, price)
                )
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while saving the invoice items: {err}", exception=err)
            conn.rollback()
            return JSONResponse(content={"success": False, "error": "Database error occurred while saving the invoice items."}, status_code=500)

    return JSONResponse(content={"success": True}, status_code=200)

@router.get("/api/ledger/invoices/get-invoice/{invoice_id}")
async def get_invoice(request: Request, invoice_id: int, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is fetching invoice {invoice_id}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT invoice_id, date, amount, is_paid, cfid FROM invoices WHERE invoice_id = ?",
                (invoice_id,)
            )
            invoice_data = cursor.fetchone()

            cursor.execute(
                "SELECT item, value FROM items_on_invoices WHERE invoice_id = ?",
                (invoice_id,)
            )
            items_data = cursor.fetchall()

            if invoice_data is None:
                return JSONResponse(content={}, status_code=404)
            else:
                items_parsed = [{"name": i[0], "price": i[1]} for i in items_data]
                return JSONResponse(
                    content={
                        "cfid": invoice_data[4],
                        "id": invoice_data[0],
                        "date": invoice_data[1],
                        "total": invoice_data[2],
                        "paid": bool(invoice_data[3]),
                        "items": items_parsed
                    },
                    status_code=200
                )
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while fetching invoice {invoice_id}: {err}", exception=err)
            conn.rollback()

class toggle_paid_data(BaseModel):
   paid: bool
   invoice_id: int

@router.post("/api/ledger/invoices/toggle-paid")
async def toggle_invoice_paid(request: Request, data: toggle_paid_data, token: str = Depends(require_prechecks)):
    body = await request.json()
    new_status = bool(body.get("paid", False))
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is toggling invoice {data.invoice_id} paid={new_status}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE invoices SET is_paid = ? WHERE invoice_id = ?",
                (new_status, data.invoice_id)
            )
            conn.commit()
            return JSONResponse(content={"success": True, "paid": new_status}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while toggling invoice paid status: {err}", exception=err)
            conn.rollback()
            return JSONResponse(content={"success": False}, status_code=500)

class add_item_data(BaseModel):
    name: str
    price: float

@router.post("/api/ledger/invoices/add-item")
async def add_possible_invoice_item(request: Request, data: add_item_data, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is adding invoice item {data.name} with value {data.price}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO invoice_items (item_id, value)
                VALUES (?, ?)
                """,
                (data.name, data.price)
            )
            conn.commit()
            return JSONResponse(content={"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while adding invoice item: {err}", exception=err)
            conn.rollback()
            return JSONResponse(content={"success": False}, status_code=500)

@router.get("/api/ledger/invoices/get-items")
async def get_invoice_items(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is listing all invoice items.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT item_id, value FROM invoice_items"
            )
            data = cursor.fetchall()
            parsed_data = []
            for item in data:
                parsed_data.append({
                    "name": item[0],
                    "price": item[1]
                })
            return JSONResponse(parsed_data, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while fetching invoice items: {err}", exception=err)
            conn.rollback()
            return JSONResponse(content={}, status_code=500)