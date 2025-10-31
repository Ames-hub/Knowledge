from library.authperms import valid_perms, set_permission, AuthPerms
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse
from library.auth import require_prechecks
from library.logbook import LogBookHandler
from fastapi.responses import JSONResponse
from library.database import DB_PATH
from library.auth import authbook
import sqlite3
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("Auth Manager System")

@router.get("/auth", response_class=HTMLResponse)
@set_permission(permission="auth_page")
async def show_auth_page(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the auth manager page.")
    return templates.TemplateResponse(
        request,
        "auth.html",
    )

@router.get("/api/auth/userlist")
@set_permission(permission="auth_page")
async def list_users(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is listing all users, their permissions, and arrested status.")
    users = authbook.list_users()
    return JSONResponse({
        "valid_permissions": valid_perms,
        "users": users
    }, status_code=200)

@router.get("/api/auth/arrest/{username}")
@set_permission(permission="auth_page")
async def arrest_user(request: Request, username: str, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} (user: {owner}) is arresting user {username}.")

    if owner == username:
        return JSONResponse(
            content={
                "success": False,
                "error": "You cannot arrest yourself."
            },
            status_code=400
        )

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE authbook SET arrested = true WHERE username = ?",
                (username,)
            )
            conn.commit()
            return HTMLResponse("User arrested successfully.", status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while arresting user: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while arresting user."}, status_code=500)

@router.get("/api/auth/release/{username}")
@set_permission(permission="auth_page")
async def arrest_user(request: Request, username: str, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is releasing user {username}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE authbook SET arrested = false WHERE username = ?",
                (username,)
            )
            conn.commit()
            return HTMLResponse("User released successfully.", status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error occurred while releasing user: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while releasing user."}, status_code=500)


@router.get("/api/auth/perm/set/{username}/{permission}/{value}")
@set_permission(permission="auth_page")
async def set_user_permission(request: Request, username: str, permission: str, value: bool, token: str = Depends(require_prechecks)):
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} (user: {owner}) is setting permission '{permission}' = {value} for user {username}.")

    if username == owner:
        return JSONResponse(
            content={
                "success": False,
                "error": "You cannot modify your own permissions."
            },
            status_code=400
        )

    value = bool(value)
    permission = str(permission).lower()

    if permission not in valid_perms:
        return JSONResponse({"success": False, "error": f"Invalid permission: {permission}"}, status_code=400)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            user_perms = AuthPerms.perms_for_user(username, fill_not_set=False)

            if user_perms.get(permission) is None:
                cursor.execute(
                    """
                    INSERT INTO auth_permissions (username, permission, allowed) VALUES (?, ?, ?)
                    """,
                    (username, permission, value)
                )
            else:
                cursor.execute(
                    """
                    UPDATE auth_permissions SET allowed = ? WHERE username = ? AND permission = ?
                    """,
                    (value, username, permission)
                )

        return JSONResponse({"success": True, "permission": permission, "value": value}, status_code=200)
    except sqlite3.OperationalError as err:
        logbook.error(f"Database error occurred while updating permission: {err}", exception=err)
        return JSONResponse({"success": False, "error": "Database error occurred while updating permission."}, status_code=500)
