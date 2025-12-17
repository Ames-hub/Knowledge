from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from decimal import Decimal, ROUND_HALF_UP, getcontext
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.authperms import set_permission
from fastapi.exceptions import HTTPException
from library.auth import require_prechecks
from library.logbook import LogBookHandler
from library.database import DB_PATH
from library.auth import authbook
from pydantic import BaseModel
from library import settings
import sqlite3
import datetime
import magic
import os
import io

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("Finance Records")

getcontext().prec = 28  # precision for financial calculations

@router.get("/ledger", response_class=HTMLResponse)
@set_permission(permission=["ledger"])
async def show_home(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the ledger.")
    return templates.TemplateResponse(
        request,
        "ledger.html",
    )

@router.get("/api/finances/load_accounts")
@set_permission(permission=["ledger"])
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
@set_permission(permission=["ledger"])
async def get_total_expenses(request: Request, account_id:int, token: str = Depends(require_prechecks)):
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) has accessed total expenses for account ID {account_id}.")
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
@set_permission(permission=["ledger"])
async def get_total_income(request: Request, account_id:int, token=Depends(require_prechecks)):
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is fetching the gross income for account ID {account_id}")
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
@set_permission(permission=["ledger"])
async def load_transactions(request: Request, account_id: int, token=Depends(require_prechecks)):
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is loading all transactions for account {account_id}")
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
@set_permission(permission=["ledger"])
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
@set_permission(permission=["ledger"])
async def get_receipt(request: Request, transaction_id: int, token=Depends(require_prechecks)):
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is getting the receipt for transaction ID {transaction_id}")
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
@set_permission(permission=["ledger"])
async def get_receipt_mime(request: Request, transaction_id: int, token=Depends(require_prechecks)):
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is getting the receipt Mime for transaction {transaction_id}")
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
@set_permission(permission=["ledger"])
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
@set_permission(permission=["ledger"])
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
@set_permission(permission=["ledger"])
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
@set_permission(permission=["ledger", "financial_planning"])
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
@set_permission(permission=["ledger", "financial_planning"])
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
@set_permission(permission=["ledger", "financial_planning"])
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
@set_permission(permission=["ledger", "financial_planning"])
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
@set_permission(permission=["ledger", "debt_tracking"])
async def debts_page(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the debts record page.")
    return templates.TemplateResponse(
        request,
        "debts.html",
    )

class debts:
    @staticmethod
    def _to_cents(amount: float) -> int:
        """Convert dollars to cents, rounding to nearest cent."""
        return int(Decimal(str(amount)).quantize(Decimal('0.01')) * 100)

    @staticmethod
    def _to_dollars(cents: int) -> float:
        """Convert cents back to dollars for display."""
        return float(Decimal(cents) / 100)

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
                        "amount": debts._to_dollars(item[3]),  # Convert cents to dollars for display
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
            "amount": debts._to_dollars(data[3]),  # Convert cents to dollars for display
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
    def create_new_debt(debtor: str, debtee: str, amount: float, description: str, start_date=None, end_date=None, cfid=None):
        if not start_date:
            start_date = datetime.datetime.now()
        
        amount_cents = debts._to_cents(amount)  # Convert to cents

        conn = sqlite3.connect(DB_PATH)

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO debts (debtor, debtee, amount, start_date, end_date, cfid)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (debtor, debtee, amount_cents, start_date, end_date, cfid)
            )
            debt_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO debt_records (debt_id, amount, description, start_date, paid_off)
                VALUES (?, ?, ?, ?, ?)
                """,
                (debt_id, amount_cents, description, start_date, False)
            )
            conn.commit()
            return debt_id
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while creating a new debt: {err}", exception=err)
            conn.rollback()
            return False

    @staticmethod
    def record_new_debt_instance(debt_id, amount: float, description, start_date=None):
        if not start_date:
            start_date = datetime.datetime.now()
        
        amount_cents = debts._to_cents(amount)  # Convert to cents
        
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE debts SET amount = amount + ? WHERE debt_id = ?
                    """,
                    (amount_cents, int(debt_id))
                )
                cursor.execute(
                    """
                    INSERT INTO debt_records (debt_id, amount, description, start_date, paid_off)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (debt_id, amount_cents, description, start_date, False)
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
                    return data[0]  # Returns cents
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while fetching a debt record amount: {err}", exception=err)
                conn.rollback()
                return False

    @staticmethod
    def subtract_debt(debt_id, paid_amount: float, record_id) -> str:
        """
        Handles debt payment.
        Returns:
        "SUB" - partially paid
        "PO" - fully paid
        "MULTI-PO" - overpaid, remainder applied to other debts
        """
        debt_amount_cents = debts.get_record_amount(record_id)  # Already in cents
        if debt_amount_cents is None:
            return False
            
        paid_cents = debts._to_cents(paid_amount)  # Convert to cents
        
        debt_amount = Decimal(debt_amount_cents)
        paid_amount_decimal = Decimal(paid_cents)

        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()

            # Update the main debt table (using float for SQLite compatibility)
            cur.execute(
                "UPDATE debts SET amount = amount - ? WHERE debt_id = ?",
                (int(paid_cents), int(debt_id))
            )

            remaining = debt_amount - paid_amount_decimal

            if remaining > 0:  # partial payment
                cur.execute(
                    "UPDATE debt_records SET amount = amount - ? WHERE record_id = ?",
                    (int(paid_cents), int(record_id))
                )
                conn.commit()
                return "SUB"

            elif remaining < 0:  # overpayment
                # pay off current record
                cur.execute(
                    "UPDATE debt_records SET amount = 0, paid_off = 1 WHERE record_id = ?",
                    (int(record_id),)
                )
                conn.commit()

                overpaid_amount_cents = -remaining  # positive Decimal

                all_debts = debts.get_debt_records(debt_id)

                for item in all_debts:
                    if overpaid_amount_cents <= 0:
                        debts.delete_debt(debt_id)
                        break
                    record_amount_cents = Decimal(all_debts[item]["amount"] * 100)  # Convert dollars back to cents
                    if record_amount_cents <= overpaid_amount_cents:
                        cur.execute(
                            "UPDATE debt_records SET amount = 0, paid_off = 1 WHERE record_id = ?",
                            (int(item),)
                        )
                        overpaid_amount_cents -= record_amount_cents
                    else:
                        cur.execute(
                            "UPDATE debt_records SET amount = amount - ? WHERE record_id = ?",
                            (int(overpaid_amount_cents), int(item))
                        )
                        overpaid_amount_cents = Decimal(0)

                if overpaid_amount_cents > 0:
                    logbook.info(f"Overpaid amount of {overpaid_amount_cents} cents could not be allocated.")
                    if settings.get.debts_overpay_payback_tracking():
                        debt_data = debts.get_debt_data(debt_id)
                        debtee = debt_data["debtee"]
                        debtor = debt_data["debtor"]  # reverse roles
                        conn.commit()
                        conn.close()
                        # Convert cents back to dollars for new debt creation
                        overpaid_dollars = float(overpaid_amount_cents / 100)
                        debts.create_new_debt(
                            debtor=debtee,
                            debtee=debtor,
                            amount=overpaid_dollars,
                            description=f"A debt with record ID {record_id} overpaid by {overpaid_dollars}."
                        )
                        debts.delete_debt(debt_id)
                        return "MULTI-PO"

                conn.commit()
                return "MULTI-PO"

            else:  # exact payment
                cur.execute(
                    "UPDATE debt_records SET amount = 0, paid_off = 1 WHERE record_id = ?",
                    (int(record_id),)
                )
                conn.commit()
                debts.delete_debt(debt_id)
                return "PO"

        except sqlite3.OperationalError as err:
            logbook.error(
                f"Database error subtracting {paid_amount} from debt {debt_id}, record {record_id}: {err}",
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
                    try:
                        datetime_obj = datetime.datetime.strptime(item[4], "%Y-%m-%d %H:%M:%S")
                    except ValueError:  # Doesn't always have the time component (for some reason. Doesn't matter too much.)
                        try:
                            datetime_obj = datetime.datetime.strptime(item[4], "%Y-%m-%d")
                        except ValueError:
                            # Enjoying the slight spaghetti? It sometimes does include microseconds, sometimes it doesn't. I'll fix this one day :3
                            datetime_obj = datetime.datetime.strptime(item[4], "%Y-%m-%d %H:%M:%S.%f")
                    parsed_data[item[0]] = {
                        "record_id": item[0],
                        "debt_id": item[1],
                        "amount": debts._to_dollars(item[2]),  # Convert cents to dollars for display
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
@set_permission(permission=["ledger", "debt_tracking"])
async def add_debt(request: Request, data: debt_data, token: str = Depends(require_prechecks)):
    debt_id = debts.find_debt_id(data.debtor, data.debtee)
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has added a debt of {data.amount} from the debt with the ID {debt_id}.")

    if data.cfid is not None:
        if data.cfid.isnumeric():
            data.cfid = int(data.cfid)
        else:
            data.cfid = None

    due_date = datetime.datetime.now().strptime(data.due_date, "%Y-%m-%d") if data.due_date else None
    start_date = datetime.datetime.now().strptime(data.start_date, "%Y-%m-%d") if data.start_date else None
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
@set_permission(permission=["ledger", "debt_tracking"])
async def subtract_debt(request: Request, data: subtract_debt_data, token = Depends(require_prechecks)):
    debt_id = debts.find_debt_id(data.debtor, data.debtee)
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has subtracted {data.amount} from the debt with ID {debt_id}.")
    try:
        debt = debts.get_debt_data(debt_id)
        if debt is None:
            return JSONResponse(content={"success": False, "error": "Debt with the given ID does not exist."}, status_code=404)

        success = debts.subtract_debt(
            debt_id=debt_id,
            paid_amount=data.amount,
            record_id=data.record_id
        )
        action = None
        if success == "SUB":
            success = True
            action = "The debt has been partially paid off"
        elif success == "PO":
            success = True
            action = "The debt has been fully paid off"
        elif success == "MULTI-PO":
            success = True
            action = "The debt has been fully paid off, and the overpaid amount has been used to pay off multiple other debts for the same."
        else:
            success = False
        
        content = {"success": success}
        if action:
            content["action"] = action
        return JSONResponse(content, status_code=200 if success else 500)
    except sqlite3.OperationalError:
        return JSONResponse(content={"success": False, "error": "Database error occurred while subtracting the debt."}, status_code=500)

@router.get("/api/finances/debts/get_all")
@set_permission(permission=["ledger", "debt_tracking"])
async def get_debts(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is listing all debts.")
    debt_list = debts.get_all_debts()
    return JSONResponse(debt_list, status_code=200)

class get_records_data(BaseModel):
    debtor: str
    debtee: str

@router.post("/api/finances/debts/get_all_records")
@set_permission(permission=["ledger", "debt_tracking"])
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
@set_permission(permission=["ledger", "invoicing"])
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
@set_permission(permission=["ledger", "invoicing"])
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
@set_permission(permission=["ledger", "invoicing"])
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
    details: dict

def get_cf_name(cfid):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT name FROM cf_names WHERE cfid = ?
                """,
                (cfid,)
            )
            data = cursor.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while fetching cf name of cfid {cfid}: {err}", exception=err)
            return False

    return data[0] if data else False

@router.post("/api/ledger/invoices/save-invoice")
@set_permission(permission=["ledger", "invoicing"])
async def save_invoice(request: Request, data: save_invoice_data, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is saving the invoice (invoice  they just made.")
    datenow = datetime.datetime.now().strftime("%d-%m-%Y")

    billing_name = data.details.get("billing_name", None)
    if not billing_name and not data.cfid:
        raise HTTPException(status_code=400, detail="Billing name is required")
    elif not billing_name and data.cfid is not None:
        # Get the name from central files.
        billing_name = get_cf_name(data.cfid)
        if billing_name is False:
            raise HTTPException(status_code=400, detail="To use a CFID for billing name, the CF profile needs to have a saved name.")

    billing_address = data.details.get("billing_address", "")
    billing_email_address = data.details.get("billing_email_address", "")
    billing_phone = data.details.get("billing_phone", "")
    billing_notes = data.details.get("billing_notes", "")

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO invoices
                (date, amount, is_paid, cfid, billing_name, billing_address, billing_email_address, billing_phone, billing_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (datenow, data.total, False, data.cfid, billing_name, billing_address, billing_email_address, billing_phone, billing_notes)
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
@set_permission(permission=["ledger", "invoicing"])
async def get_invoice(request: Request, invoice_id: int, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is fetching invoice {invoice_id}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT invoice_id, date, amount, is_paid, cfid, billing_name, billing_address, billing_email_address, billing_phone, billing_notes
                FROM invoices
                WHERE invoice_id = ?
                """,
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
                        "items": items_parsed,
                        "billing_name": invoice_data[4],
                        "billing_address": invoice_data[5],
                        "billing_email_address": invoice_data[6],
                        "billing_phone": invoice_data[7],
                        "billing_notes": invoice_data[8],
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
@set_permission(permission=["ledger", "invoicing"])
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
@set_permission(permission=["ledger", "invoicing"])
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
@set_permission(permission=["ledger", "invoicing"])
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