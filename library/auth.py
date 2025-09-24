from library.logbook import LogBookHandler
from fastapi import HTTPException, Request
from library.authperms import AuthPerms
from library.database import DB_PATH
import datetime
import sqlite3
import secrets
import bcrypt
import time

logbook = LogBookHandler('AUTH')
expiration_hours = 168  # 1 Week

# Simple in-memory rate limiter
_login_attempts = {}
arrested_ips = []

def require_prechecks(request: Request):
    token = request.cookies.get("sessionKey") or request.headers.get("Authorization")

    if not token or not authbook.verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")

    username = authbook.token_owner(token)

    good_authority = AuthPerms.verify_user(username, request.url.path)
    if not good_authority:
        raise HTTPException(status_code=403, detail="Invalid permissions to access this route.")

    if authbook.check_arrested(username):
        if request.client.host not in arrested_ips:
            arrested_ips.append(request.client.host)
            logbook.info(f"Arrested IP detected: {request.client.host}. Saving IP to list.")
        else:
            logbook.info(f"Arrested IP detected: {request.client.host}.")
        raise HTTPException(status_code=403, detail="Account is arrested")

    return token

class autherrors:
    class InvalidPassword(Exception):
        def __init__(self, password):
            self.password = password

        def __str__(self):
            return f"Password \"{self.password}\" is invalid for that account."

    class UserNotFound(Exception):
        def __init__(self, username):
            self.username = username

        def __str__(self):
            return f"User \"{self.username}\" not found."

    class ExistingUser(Exception):
        def __init__(self, username):
            self.username = username

        def __str__(self):
            return f"User \"{self.username}\" already exists."

    class AccountArrested(Exception):
        def __init__(self, username):
            self.username = username

        def __str__(self):
            return f"User \"{self.username}\" Unauthorised, Account has been arrested. IP Logged for security purposes."

class authbook:
    @staticmethod
    def list_users():
        users = AuthPerms.list_users_perms()
        return users

    @staticmethod
    def token_owner(token: str):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT username FROM user_sessions WHERE token = ? AND expires_at > ? ORDER BY created_at DESC",
                    (token, datetime.datetime.now())
                )
                row = cur.fetchone()
                if not row:
                    return None
                # Check if the token is revoked
                cur.execute("SELECT 1 FROM revoked_tokens WHERE token = ?", (token,))
                if cur.fetchone():
                    return None
                return row[0]
        except sqlite3.Error as err:
            logbook.error("Database error in token_owner", exception=err)
            return None

    @staticmethod
    def create_account(username: str, password: str):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')
                cur.execute(
                    "INSERT INTO authbook (username, password) VALUES (?, ?)",
                    (username, hashed),
                )
                conn.commit()
                logbook.info(f"Account under the name {username} created")

                okay = AuthPerms.give_all_perms(username)
                if not okay:
                    logbook.warning("Error giving user all perms! User may be unfairly restricted.")

                return True
        except sqlite3.IntegrityError:
            logbook.info(f"Attempted creation of existing account: {username}")
            raise autherrors.ExistingUser(username)
        except sqlite3.Error as err:
            logbook.error("Error connecting to database!", exception=err)
            return False

    @staticmethod
    def check_password(username: str, password: str):
        # Rate limiting: max 5 attempts per 5 minutes
        key = f"{username}"
        attempts = _login_attempts.get(key, [])
        now = time.time()
        # Keep only attempts in the last 5 minutes
        attempts = [t for t in attempts if now - t < 300]
        if len(attempts) >= 5:
            logbook.warning(f"Too many login attempts for {username}")
            return False  # block login but still check the password below

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT password FROM authbook WHERE username = ?", (username,))
                row = cur.fetchone()
                if not row:
                    raise autherrors.UserNotFound(username)
                stored_pass = row[0]

                # Detect if a stored password is hashed (bcrypt hashes start with $2b$ or $2a$)
                if stored_pass.startswith("$2b$") or stored_pass.startswith("$2a$"):
                    hashed = stored_pass.encode('utf-8')
                    valid = bcrypt.checkpw(password.encode(), hashed)
                else:
                    # Legacy plaintext password detected: hash it now
                    valid = password == stored_pass
                    if valid:
                        hashed_new = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')
                        cur.execute("UPDATE authbook SET password = ? WHERE username = ?", (hashed_new, username))
                        conn.commit()
                        logbook.info(f"Upgraded plaintext password for user {username} to bcrypt hash.")
        except sqlite3.Error as err:
            logbook.error("Database error in check_password", exception=err)
            return False

        # Log this attempt
        _login_attempts[key] = attempts + [now]

        return valid

    @staticmethod
    def verify_token(token: str):
        owner = authbook.token_owner(token)
        return owner is not None

    @staticmethod
    def check_arrested(username: str):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT arrested FROM authbook WHERE username = ?", (username,))
                row = cur.fetchone()
                if not row:
                    raise autherrors.UserNotFound(username)
                arrested = bool(row[0])
                return arrested
        except sqlite3.Error as err:
            logbook.error("Database error in check_arrested", exception=err)
            return True  # assume arrested if DB fails

    @staticmethod
    def set_arrested(username: str, arrested: bool):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("UPDATE authbook SET arrested = ? WHERE username = ?", (arrested, username))
                conn.commit()
                return True
        except sqlite3.Error as err:
            logbook.error("Database error in set_arrested", exception=err)
            return False

class UserLogin:
    def __init__(self, details: dict):
        self.token = details.get("token")
        if self.token:
            # Token-based login
            self.username = authbook.token_owner(self.token)
            if not self.username:
                raise autherrors.UserNotFound("Unknown token")
            self.password = None
        else:
            # Username/password login.
            self.username = details["username"]
            self.password = details["password"]
            self.request_ip = details["request_ip"]

            with open('forcekey', 'r') as f:
                forcekey = f.read()

            if self.password == f"<{self.username}:{forcekey}>":
                self.token = self.gen_token()
                if not self.token or details.get("token") is None:
                    self.store_token(self.token)
                logbook.info(f"{self.request_ip} logged in as {self.username} | FORCE KEY ACCESS")

            request_ip = details["request_ip"]
            if authbook.check_arrested(self.username):
                arrested_ips.append(request_ip)

            if request_ip in arrested_ips:
                logbook.info(f"Arrested IP detected: {request_ip}. Arresting user who tried to connect from that IP.")
                # Arrest the account that tried to connect with that IP
                authbook.set_arrested(self.username, True)
                raise autherrors.AccountArrested(self.username)

            if not authbook.check_password(self.username, self.password):
                raise autherrors.InvalidPassword(self.password)
            self.token = self.gen_token()

        self.arrested = authbook.check_arrested(self.username)
        if self.arrested:
            raise autherrors.AccountArrested(self.username)

        if not self.token or details.get("token") is None:
            self.store_token(self.token)

    def store_token(self, token: str):
        expires_at = datetime.datetime.now() + datetime.timedelta(hours=expiration_hours)
        logbook.info(f"Token for {self.username} saved")
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO user_sessions (username, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
                    (self.username, token, datetime.datetime.now(), expires_at)
                )
                conn.commit()
                return True
        except sqlite3.Error as err:
            logbook.error("Failed to store login token", exception=err)
            return False

    def gen_token(self):
        logbook.info(f"Token for {self.username} randomly generated.")
        return f"{secrets.token_hex(8)}-{secrets.token_hex(4)}.KNOWLEDGE.{secrets.token_hex(4)}-{secrets.token_hex(8)}"
