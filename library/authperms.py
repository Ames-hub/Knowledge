from library.settings import make_settings_file, SETTINGS_PATH
from library.logbook import LogBookHandler
from library.database import DB_PATH
from fastapi import Request
from functools import wraps
import sqlite3
import json
import os

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

def set_permission(permission: str):
    """
    Used for adding a permission requirement to a route at launch.
    Automatically uses the route template, ignoring dynamic parameters.
    """
    if not os.path.exists(SETTINGS_PATH):
        make_settings_file()

    def decorator(route_func):
        @wraps(route_func)
        async def wrapper(request: Request, *args, **kwargs):
            # Use the route template from FastAPI, not the full path that'll have used parameters and stuff.
            path = request.scope.get("route").path

            # remove trailing slash
            if path != '/' and path.endswith('/'):
                path = path[:-1]

            with open(SETTINGS_PATH, 'r') as file:
                data = json.load(file)

            if data.get("route_perms") is None:
                data['route_perms'] = {}
            data['route_perms'][path] = permission

            with open(SETTINGS_PATH, 'w') as file:
                json.dump(data, file, indent=4, separators=(',', ': '))

            return await route_func(request, *args, **kwargs)

        return wrapper
    return decorator

def get_permission(route: str):
    with open('settings.json', 'r') as file:
        data = json.load(file)
        if data.get("route_perms", None) is None:
            return None
        if route not in data["route_perms"].keys():
            return None
        return data["route_perms"][route]


excepted_routes = [
    '/',
    '/register',
    '/login',
    '/favicon.ico'
]

class AuthPerms:
    @staticmethod
    def verify_user(username, requested_route:str):
        user_perms = AuthPerms.perms_for_user(username)

        if requested_route.startswith('/static/'):
            return True  # This is for a JS or CSS file. Not this things job.
        if requested_route in excepted_routes:
            return True

        for perm_name in user_perms:
            needed_perm = get_permission(requested_route)
            if not needed_perm:
                logbook.info(f"Route \"{requested_route}\" is missing permission requirements, please consider adding them. "
                             "If you won't, add them to exceptions.\"")
                return True

            if perm_name == needed_perm:
                perm_allowed = user_perms[perm_name]
                if perm_allowed is True:
                    allowed = True
                    break
        else:
            allowed = False

        return allowed

    @staticmethod
    def give_all_perms(username):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            try:
                for perm in valid_perms:
                    cursor.execute(
                        """
                        INSERT INTO auth_permissions (username, permission, allowed) VALUES (?, ?, ?)
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
                logbook.error(f"Database error occurred while listing the user, their perms and arrested status: {err}", exception=err)
                conn.rollback()

            user_perms = {}
            for row in perms_data:
                if row[0] in valid_perms:
                    user_perms[row[0]] = bool(row[1])
                else:
                    logbook.warning(f"User {username} has an invalid, illegal permission: {row[0]}")

            # Specify any perms not listed
            if fill_not_set:
                for perm_name in user_perms:
                    for valid_perm in valid_perms:
                        if valid_perm not in user_perms:
                            user_perms[perm_name] = True

            return user_perms

    @staticmethod
    def list_users_perms():
        with sqlite3.connect(DB_PATH) as conn:
            # Selects all users
            try:
                cur = conn.cursor()
                cur.execute("SELECT username, arrested FROM authbook")
                users_data = cur.fetchall()
            except sqlite3.OperationalError as err:
                logbook.error(f"Database error occurred while listing users, their perms and arrested status: {err}",
                              exception=err)
                conn.rollback()
                return False

            user_list = [row[0] for row in users_data]

            for username in user_list:
                try:
                    cur.execute("SELECT permission, allowed FROM auth_permissions WHERE username = ?", (username,))
                    perms_data = cur.fetchall()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Database error occurred while listing users, their perms and arrested status: {err}", exception=err)
                    conn.rollback()
                    continue

            users = {}
            for row in users_data:
                perms = {}
                for perm in perms_data:
                    if perm[0] not in valid_perms:
                        logbook.info(f"Invalid perm for user {row[0]}: {perm[0]}")
                        continue
                    if bool(perm[1]):
                        perms[perm[0]] = True
                    else:
                        perms[perm[0]] = False
                users[row[0]] = {
                    "permissions": perms,
                    "arrested": bool(row[1])
                }
        return users