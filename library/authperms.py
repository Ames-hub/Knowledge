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

logbook = LogBookHandler("AUTH-PERMS")

valid_perms = [
    'central_files',
    'bulletin_archives',
    'app_logs',
    'ledger',
    'dianetics',
    'battleplans',
    'ftp_server',
    'auth_page',
    'app_settings',
    'signal_server'
]


def lock_and_load_settings(path: str):
    """Safely open and read a JSON settings file with a blocking file lock."""
    with open(path, 'r') as f:
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_SH)
                data = json.load(f)
                break
            except json.JSONDecodeError:
                time.sleep(0.05)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    return data


def lock_and_write_settings(path: str, data: dict):
    """Safely write JSON to settings file using blocking file lock."""
    with open(path, 'r+') as f:
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.seek(0)
                json.dump(data, f, indent=4, separators=(',', ': '))
                f.truncate()
                break
            except OSError:
                time.sleep(0.05)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)


def set_permission(permission):
    """
    Add permission requirement(s) to a route at launch.
    Supports multiple permissions (list or single string).
    """
    if not os.path.exists(SETTINGS_PATH):
        make_settings_file()

    def decorator(route_func):
        @wraps(route_func)
        async def wrapper(request: Request, *args, **kwargs):
            path = request.scope.get("route").path

            if path != '/' and path.endswith('/'):
                path = path[:-1]

            data = lock_and_load_settings(SETTINGS_PATH)
            if data.get("route_perms") is None:
                data['route_perms'] = {}

            # Normalize permissions into a list
            perms = permission if isinstance(permission, list) else [permission]
            data['route_perms'][path] = perms

            lock_and_write_settings(SETTINGS_PATH, data)

            return await route_func(request, *args, **kwargs)

        return wrapper
    return decorator


def get_permission(route: str):
    """Return the permission(s) required for a given route."""
    if not os.path.exists('settings.json'):
        return None
    data = lock_and_load_settings('settings.json')
    route_perms = data.get("route_perms")
    if not route_perms:
        return None

    # Exact match first
    if route in route_perms:
        return route_perms[route]

    # Fallback: try to match dynamic path templates like /api/files/{id}/profile_icon
    for pattern_route, perms in route_perms.items():
        # Convert {param} or :param style placeholders into regex wildcards
        pattern = re.sub(r"\{[^/]+\}", r"[^/]+", pattern_route)
        if re.fullmatch(pattern, route):
            return perms

    return None


excepted_routes = [
    '/',
    '/register',
    '/login',
    '/favicon.ico'
]


class AuthPerms:
    @staticmethod
    def verify_user(username, requested_route: str):
        user_perms = AuthPerms.perms_for_user(username)

        if requested_route.startswith('/static/'):
            return True
        if requested_route in excepted_routes:
            return True

        needed_perms = get_permission(requested_route)
        if not needed_perms:
            # Only log missing perms if no dynamic pattern matched
            # (means truly undefined, not just dynamic route)
            logbook.info(
                f"Route \"{requested_route}\" has no defined permission set. "
                "If it's intentional, add it to exceptions."
            )
            return True

        # Normalize user perms
        for perm in needed_perms:
            if perm in user_perms and user_perms[perm] is True:
                return True
        return False

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
                cur.execute("SELECT permission, allowed FROM auth_permissions WHERE username = ?", (username,))
                perms_data = cur.fetchall()
            except sqlite3.OperationalError as err:
                logbook.error(
                    f"Database error occurred while listing perms for user {username}: {err}",
                    exception=err
                )
                conn.rollback()
                perms_data = []

            user_perms = {}
            for row in perms_data:
                if row[0] in valid_perms:
                    user_perms[row[0]] = bool(row[1])
                else:
                    logbook.warning(f"User {username} has an invalid permission: {row[0]}")

            if fill_not_set:
                for valid_perm in valid_perms:
                    if valid_perm not in user_perms:
                        user_perms[valid_perm] = True

            return user_perms

    @staticmethod
    def list_users_perms():
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT username, arrested FROM authbook")
                users_data = cur.fetchall()
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while listing users: {err}", exception=err)
                conn.rollback()
                return False

            users = {}
            for username, arrested in users_data:
                try:
                    cur.execute("SELECT permission, allowed FROM auth_permissions WHERE username = ?", (username,))
                    perms_data = cur.fetchall()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Database error occurred for user {username}: {err}", exception=err)
                    conn.rollback()
                    continue

                perms = {}
                for perm, allowed in perms_data:
                    if perm not in valid_perms:
                        logbook.info(f"Invalid perm for user {username}: {perm}")
                        continue
                    perms[perm] = bool(allowed)

                users[username] = {
                    "permissions": perms,
                    "arrested": bool(arrested)
                }

        return users
