from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from library.logbook import LogBookHandler
from fastapi import HTTPException, Request
from cryptography.x509.oid import NameOID
from library.authperms import AuthPerms
from library.database import DB_PATH
from cryptography import x509
import datetime
import sqlite3
import secrets
import bcrypt
import time
import os
import shutil

logbook = LogBookHandler('AUTH')
expiration_hours = 168  # 1 Week

# Simple in-memory rate limiter
_login_attempts = {}
arrested_ips = []


# -----------------------------
# Utility Helpers
# -----------------------------
def flag_ip(ip):
    if ip and ip not in arrested_ips:
        arrested_ips.append(ip)
        logbook.info(f"Arrested IP detected: {ip}. Saving IP to list.")


# -----------------------------
# Certificate
# -----------------------------
def generate_self_signed_cert(country_name, province_name, locality_name, organisation_name, common_name="localhost", valid_days=365):
    key_file = "certs/key.pem"
    cert_file = "certs/cert.pem"

    if os.path.exists("certs"):
        shutil.rmtree("certs", ignore_errors=True)
    os.makedirs("certs", exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, country_name),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, province_name),
        x509.NameAttribute(NameOID.LOCALITY_NAME, locality_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organisation_name),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=valid_days))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(common_name)]), critical=False)
        .sign(key, hashes.SHA256())
    )

    with open(key_file, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    return {"cert_file": cert_file, "key_file": key_file}


# -----------------------------
# Central Access Validator
# -----------------------------
def validate_access(token: str, path: str, ip=None, do_ip_ban=False):
    if not token:
        return {"ok": False, "reason": "NO_TOKEN"}

    username = authbook.token_owner(token)
    if not username:
        return {"ok": False, "reason": "INVALID_TOKEN"}

    if authbook.check_arrested(username):
        if do_ip_ban:
            flag_ip(ip)
        return {"ok": False, "reason": "ARRESTED", "username": username}

    if not AuthPerms.verify_user(username, path):
        return {"ok": False, "reason": "NO_PERMISSION", "username": username}

    return {"ok": True, "username": username}


# -----------------------------
# Request Helpers
# -----------------------------
def require_prechecks(request: Request):
    token = request.cookies.get("sessionKey") or request.headers.get("Authorization")
    result = validate_access(token, request.url.path, request.client.host)

    if not result["ok"]:
        raise HTTPException(status_code=403, detail=result["reason"])

    return token


def check_valid_login(token, url_target, client_ip, do_IP_ban: bool = False):
    result = validate_access(token, url_target, client_ip, do_IP_ban)
    return [result["ok"], result.get("reason")]


def get_user(request: Request):
    token = request.cookies.get("sessionKey") or request.headers.get("Authorization")
    if not token:
        return {"token": None, "username": None}

    username = authbook.token_owner(token)
    return {"token": token, "username": username}


# -----------------------------
# Errors
# -----------------------------
class autherrors:
    class InvalidPassword(Exception): ...
    class UserNotFound(Exception): ...
    class ExistingUser(Exception): ...
    class AccountArrested(Exception): ...


# -----------------------------
# Authbook
# -----------------------------
class authbook:
    @staticmethod
    def create_account(username:str, password:str, is_admin:bool=None):
        user_count = len(authbook.list_users())

        # Checks if there are 0 other accounts. First account is admin always
        if is_admin is None:
            is_admin = user_count == 0

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')
                cur.execute(
                    "INSERT INTO authbook (username, password, admin) VALUES (?, ?, ?)",
                    (username, hashed, is_admin),
                )
                conn.commit()
                logbook.info(f"Account under the name {username} created")

                if is_admin:
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

                cur.execute("SELECT 1 FROM revoked_tokens WHERE token = ?", (token,))
                if cur.fetchone():
                    return None

                return row[0]
        except sqlite3.Error as err:
            logbook.error("Database error in token_owner", exception=err)
            return None

    @staticmethod
    def is_user_admin(username):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT admin FROM authbook WHERE username = ?",
                    (username,)
                )
                row = cur.fetchone()
                if not row:
                    return False
                return bool(row[0])
        except sqlite3.Error as err:
            logbook.error("Database error fetching is user is admin", exception=err)
            return None
    @staticmethod
    def verify_token(token: str):
        return authbook.token_owner(token) is not None

    @staticmethod
    def check_arrested(username: str):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT arrested FROM authbook WHERE username = ?", (username,))
                row = cur.fetchone()
                return bool(row[0]) if row else True
        except sqlite3.Error:
            return True

    @staticmethod
    def check_password(username: str, password: str):
        key = username
        attempts = _login_attempts.get(key, [])
        now = time.time()

        attempts = [t for t in attempts if now - t < 300]

        if len(attempts) >= 5:
            _login_attempts[key] = attempts
            logbook.warning(f"Too many login attempts for {username}")
            return False

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT password FROM authbook WHERE username = ?", (username,))
                row = cur.fetchone()
                if not row:
                    return False

                stored_pass = row[0]

                if stored_pass.startswith("$2"):
                    valid = bcrypt.checkpw(password.encode(), stored_pass.encode())
                else:
                    valid = password == stored_pass
                    if valid:
                        hashed_new = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                        cur.execute("UPDATE authbook SET password = ? WHERE username = ?", (hashed_new, username))
                        conn.commit()
        except sqlite3.Error:
            return False

        _login_attempts[key] = attempts + [now]
        return valid

    @staticmethod
    def list_users():
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT username, arrested, admin FROM authbook")
                rows = cur.fetchall()
        except sqlite3.Error as err:
            logbook.error("Error fetching users!", exception=err)
            return []
        
        data = {}
        for row in rows:
            data[row[0]] = {
                "username": row[0],
                "arrested": row[1],
                "is_admin": row[2],
                "permissions": AuthPerms.perms_for_user(row[0])
            }
        return data

# -----------------------------
# User Login
# -----------------------------
class UserLogin:
    def __init__(self, details: dict):
        self.token = details.get("token")
        self.logged_via_forcekey = False

        if self.token:
            self.username = authbook.token_owner(self.token)
            if not self.username:
                raise Exception("Invalid token")
            self.password = None
        else:
            self.username = details["username"]
            self.password = details["password"].strip()
            self.request_ip = details["request_ip"]

            if not authbook.check_password(self.username, self.password):
                raise Exception("Invalid password")

            self.token = self.gen_token()

        if authbook.check_arrested(self.username):
            flag_ip(details.get("request_ip"))
            raise Exception("Account arrested")

        self.store_token(self.token)

    def store_token(self, token: str):
        expires_at = datetime.datetime.now() + datetime.timedelta(hours=expiration_hours)
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO user_sessions (username, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (self.username, token, datetime.datetime.now(), expires_at)
            )
            conn.commit()

    def gen_token(self):
        return f"{secrets.token_hex(8)}-{secrets.token_hex(4)}.KNOWLEDGE.{secrets.token_hex(4)}-{secrets.token_hex(8)}"
