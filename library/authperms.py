from library.settings import make_settings_file, SETTINGS_PATH
from library.logbook import LogBookHandler
from library.database import DB_PATH
from fastapi import Request
from functools import wraps
import sqlite3
import fcntl
import json
import time
import os
import re
from threading import Lock

logbook = LogBookHandler("AUTH-PERMS")

valid_perms = [
    'central_files',
    'bulletin_archives',
    'app_logs',

    # Finances
    'ledger',

    'accounts_view',
    'accounts_add',
    'accounts_delete',
    'accounts_add_transaction',
    'accounts_del_transaction',

    'invoices_view',
    'invoices_create',
    'invoices_delete',
    'invoices_modify',

    'debt_viewing',
    'debt_editting',
    
    'FP_edit',
    'FP_view',
    
    # Other
    'dianetics',
    'battleplans',
    'ftp_server',
    'admin_panel',
    'signal_server',
    'odometering'
]

_settings_write_lock = Lock()
_registered_routes = set()


def lock_and_load_settings(path: str):
    if not os.path.exists(path):
        make_settings_file()

    with open(path, 'r') as f:
        locked = False
        try:
            while True:
                try:
                    fcntl.flock(f, fcntl.LOCK_SH)
                    locked = True
                    return json.load(f)
                except json.JSONDecodeError:
                    time.sleep(0.05)
                finally:
                    if locked:
                        fcntl.flock(f, fcntl.LOCK_UN)
                        locked = False
        finally:
            if locked:
                fcntl.flock(f, fcntl.LOCK_UN)


def lock_and_write_settings(path: str, data: dict):
    with _settings_write_lock:
        with open(path, 'r+') as f:
            locked = False
            try:
                while True:
                    try:
                        fcntl.flock(f, fcntl.LOCK_EX)
                        locked = True
                        f.seek(0)
                        json.dump(data, f, indent=4, separators=(',', ': '))
                        f.truncate()
                        return
                    except OSError:
                        time.sleep(0.05)
                    finally:
                        if locked:
                            fcntl.flock(f, fcntl.LOCK_UN)
                            locked = False
            finally:
                if locked:
                    fcntl.flock(f, fcntl.LOCK_UN)


def _normalize_path(path: str):
    if path != '/' and path.endswith('/'):
        return path[:-1]
    return path


def set_permission(permission):
    perms = permission if isinstance(permission, list) else [permission]

    def decorator(route_func):
        @wraps(route_func)
        async def wrapper(request: Request, *args, **kwargs):
            path = _normalize_path(request.scope.get("route").path)

            if path not in _registered_routes:
                with sqlite3.connect(DB_PATH) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "CREATE TABLE IF NOT EXISTS route_permissions (route TEXT PRIMARY KEY, permissions TEXT)"
                    )

                    cur.execute(
                        "SELECT permissions FROM route_permissions WHERE route = ?",
                        (path,)
                    )
                    row = cur.fetchone()
                    perms_json = json.dumps(perms)
                    if not row:
                        cur.execute(
                            "INSERT INTO route_permissions (route, permissions) VALUES (?, ?)",
                            (path, perms_json)
                        )
                    elif row[0] != perms_json:
                        cur.execute(
                            "UPDATE route_permissions SET permissions = ? WHERE route = ?",
                            (perms_json, path)
                        )
                    conn.commit()

                _registered_routes.add(path)

            return await route_func(request, *args, **kwargs)

        return wrapper
    return decorator


def get_permission(route: str):
    route = _normalize_path(route)

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT route, permissions FROM route_permissions"
        )
        rows = cur.fetchall()

    # rows now contains tuples like: ('/ledger/debts', '["ledger", "debt_viewing"]')
    route_perms = {r: json.loads(p) for r, p in rows}

    if route in route_perms:
        return route_perms[route]

    # Dynamic fallback (parameterized routes)
    for pattern_route, perms in route_perms.items():
        escaped = re.escape(pattern_route)
        pattern = re.sub(r"\\\{[^/]+\\\}", r"[^/]+", escaped)
        if re.fullmatch(pattern, route):
            return perms

    return None


excepted_routes = [
    '/',
    '/register',
    '/login',
    '/favicon.ico',
    '/apps'
]


class AuthPerms:
    @staticmethod
    def verify_user(username, requested_route: str):
        requested_route = _normalize_path(requested_route)

        # Allow static and excepted routes
        if requested_route.startswith('/static/'):
            return True
        if requested_route in excepted_routes:
            return True

        needed_perms = get_permission(requested_route)
        if not needed_perms:
            logbook.info(f'Route "{requested_route}" has no defined permission set.')
            return True

        # Ensure needed_perms is always a list
        if isinstance(needed_perms, str):
            needed_perms = [needed_perms]

        user_perms = AuthPerms.perms_for_user(username)

        # Check each required permission
        for perm in needed_perms:
            if not user_perms.get(perm, False):
                perms_str = ", ".join([p for p, a in user_perms.items() if a]) or "no permissions"
                logbook.info(f'{username} missing permission "{perm}". Has {perms_str}')
                return False

        return True

    @staticmethod
    def check_allowed(username: str, permissions: str | list):
        user_perms = AuthPerms.perms_for_user(username)

        if isinstance(permissions, str):
            return bool(user_perms.get(permissions, False))

        return all(user_perms.get(p, False) for p in permissions)

    @staticmethod
    def give_all_perms(username):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            try:
                for perm in valid_perms:
                    cursor.execute(
                        """
                        INSERT INTO auth_permissions (username, permission, allowed)
                        VALUES (?, ?, ?)
                        """,
                        (username, perm, True)
                    )
                conn.commit()
                return True
            except sqlite3.OperationalError as err:
                logbook.error("Error giving user all perms!", exception=err)
                conn.rollback()
                return False

    @staticmethod
    def perms_for_user(username, fill_not_set=True):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT permission, allowed FROM auth_permissions WHERE username = ?",
                    (username,)
                )
                perms_data = cur.fetchall()
            except sqlite3.OperationalError as err:
                logbook.error(
                    f"Database error while listing perms for {username}: {err}",
                    exception=err
                )
                conn.rollback()
                perms_data = []

        user_perms = {
            perm: bool(allowed)
            for perm, allowed in perms_data
            if perm in valid_perms
        }

        from library.auth import authbook
        if fill_not_set:
            is_admin = authbook.is_user_admin(username)
            for valid_perm in valid_perms:
                user_perms.setdefault(valid_perm, is_admin)

        return user_perms

    @staticmethod
    def list_users_perms():
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT username, arrested, admin FROM authbook")
                users_data = cur.fetchall()
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error while listing users: {err}", exception=err)
                conn.rollback()
                return False

            users = {}
            for username, arrested, is_admin in users_data:
                cur.execute(
                    "SELECT permission, allowed FROM auth_permissions WHERE username = ?",
                    (username,)
                )
                perms_data = cur.fetchall()

                perms = {
                    perm: bool(allowed)
                    for perm, allowed in perms_data
                    if perm in valid_perms
                }

                users[username] = {
                    "permissions": perms,
                    "arrested": bool(arrested),
                    "is_admin": bool(is_admin)
                }

        return users
