from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.authperms import valid_perms, set_permission, AuthPerms
from library.auth import require_prechecks, authbook
from library.logbook import LogBookHandler
from library.database import DB_PATH
from pydantic import BaseModel
from library import settings
import sqlite3
import json
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("Admin Panel")

# ===== Admin Panel Main Page =====
@router.get("/knowledge", response_class=HTMLResponse)
@set_permission(permission="admin_panel")
async def show_admin_panel(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the admin panel.")
    return templates.TemplateResponse(
        request,
        "admin.html",
    )

# ===== Auth Management Endpoints =====
@router.get("/api/knowledge/userlist")
@set_permission(permission="admin_panel")
async def list_users(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is listing all users.")
    users = authbook.list_users()
    return JSONResponse({
        "valid_permissions": valid_perms,
        "users": users
    }, status_code=200)

@router.get("/api/knowledge/arrest/{username}")
@set_permission(permission="admin_panel")
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

    if authbook.is_user_admin(username):
        return JSONResponse(
            content={
                "success": False,
                "error": "You cannot arrest an admin user."
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
            return JSONResponse({"success": True, "message": "User arrested successfully."}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while arresting user: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred."}, status_code=500)

@router.get("/api/knowledge/release/{username}")
@set_permission(permission="admin_panel")
async def release_user(request: Request, username: str, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is releasing user {username}.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE authbook SET arrested = false WHERE username = ?",
                (username,)
            )
            conn.commit()
            return JSONResponse({"success": True, "message": "User released successfully."}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while releasing user: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred."}, status_code=500)

@router.get("/api/knowledge/perm/set/{username}/{permission}/{value}")
@set_permission(permission="admin_panel")
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
    if authbook.is_user_admin(username):
        return JSONResponse(
            content={
                "success": False,
                "error": "You cannot modify permissions for an admin user."
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
            conn.commit()
        return JSONResponse({"success": True, "permission": permission, "value": value}, status_code=200)
    except sqlite3.OperationalError as err:
        logbook.error(f"Database error while updating permission: {err}", exception=err)
        return JSONResponse({"success": False, "error": "Database error occurred."}, status_code=500)

# ===== Settings Management Endpoints =====
class SettingsData(BaseModel):
    config: dict

@router.get("/api/knowledge/settings/load")
@set_permission(permission="admin_panel")
async def load_settings(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is loading settings.")
    try:
        with open('settings.json', 'r') as f:
            data = json.load(f)
        
        del data['route_perms']  # Hide sensitive data
        return JSONResponse(data)
    except Exception as err:
        logbook.error(f"Error loading settings: {err}", exception=err)
        return JSONResponse({"error": "Failed to load settings"}, status_code=500)

@router.post("/api/knowledge/settings/save")
@set_permission(permission="admin_panel")
async def save_settings(request: Request, data: SettingsData, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is saving settings.")
    for setting, value in data.config.items():
        setting = str(setting).lower()
        if setting not in settings.valid_settings.keys():
            return JSONResponse(
                content={"success": False, "error": f"Setting key '{setting}' is invalid."},
                status_code=400
            )
        try:
            settings.save(key=setting, value=value)
        except Exception as err:
            logbook.error(f"Error saving setting '{setting}': {err}", exception=err)
            return JSONResponse(
                content={"success": False, "error": f"Failed to save setting '{setting}'."},
                status_code=500
            )
    return JSONResponse({"success": True, "message": "Settings saved successfully."})