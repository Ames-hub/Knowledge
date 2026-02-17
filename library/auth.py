from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from library.logbook import LogBookHandler
from fastapi import HTTPException, Request
from cryptography.x509.oid import NameOID
from library.authperms import AuthPerms
from library.settings import get, save
from library.database import DB_PATH
from cryptography import x509
import subprocess
import datetime
import sqlite3
import secrets
import bcrypt
import shutil
import time
import os

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

def get_ssl_filepaths(domain:str=None):
    """
    Returns:
    keyfile_path, certfile_path
    """
    if not domain:
        domain = get.domain()
    key_file = f"certs/key.pem"
    cert_file = f"certs/cert.pem"
    return key_file, cert_file

# -----------------------------
# Certificates
# -----------------------------
def generate_certbot_cert(
    domain: str, 
    email: str, 
    interactive: bool = True,
    force_renewal: bool = False
) -> bool:
    """
    Generate a DNS-01 cert for a domain using Certbot in true manual mode.

    :param domain: Domain to generate cert for
    :param email: Your email
    :param interactive: If True, Certbot will pause for you to manually add TXT record
    :return: True if successful, False otherwise
    """
    import os, subprocess, datetime

    os.makedirs('certs', exist_ok=True)

    try:
        cmd = [
            "sudo",
            "certbot",
            "certonly",
            "--manual",
            "--preferred-challenges", "dns",
            "-d", domain,
            "-m", email,
            "--agree-tos",
            "--manual-public-ip-logging-ok",
        ]

        if force_renewal:
            cmd += ["--force-renewal"]

        # Only non-interactive if interactive=False
        if not interactive:
            cmd += ["--non-interactive"]

        # Run certbot
        result = subprocess.run(cmd, check=True)

        # Fix permissions
        subprocess.run(['sudo', 'chmod', '-R', '755', './certs'])

        # Save SSL expiration time
        expiration = datetime.datetime.now() + datetime.timedelta(days=90)
        save("time_to_ssl_expiration", value=expiration.timestamp())

        return result.returncode == 0

    except subprocess.CalledProcessError as e:
        logbook.error(f"Certbot failed for domain {domain}: {e}")
        return False

def setup_certbot_ssl():
    domain = get.domain()
    if not domain:
        print("What is the domain of your website for this certificate? eg, google.com")
        domain = input(">>> ")
        save("domain", domain)
    email_address = get.domain_email()
    if not email_address:
        print("What's the email address you wish to use for the certificate?")
        email_address = input(">>> ")
        save("domain_email", email_address)

    success = generate_certbot_cert(
        domain=domain,
        email=email_address
    )
    print(f"SSL Setup success: {success}")
    if not success:
        print("Success failure. Defaulting to self-signed certs.")
        setup_selfsigned()

    print("NOTICE: You will be required to do this every 90 days to keep up with Certbot's renewment policy.")
    print("We will notify you.")
    # TODO: Fix and make sure auto-renewing works. 
    return True
    print("Would you like to setup auto-renewing for the Certificates? (y/n)")

    do_auto_renew = input(">>> ") == "y"
    if not do_auto_renew:
        return True

    # Setup auto-renew
    print("There are two currently accepted providers for auto-renewing DNS's")
    print("Please pick one by its number.")
    print("1. Dynu.com (recommended)")
    print("2. Cloudflare.com")
    option = int(input(">>> "))
    providers = {
        1: "dynu",
        2: "cloudflare"
    }
    provider = providers[option]
    save("dns_provider", provider)

    print(f"What is your API Token for {provider}?")
    api_token = input(">>> ")
    save("dns_token", api_token)

    print("What did you set the record name as? (default: _acme-challenge)")
    record_name = input(">>> ")
    if not record_name:
        record_name = "_acme-challenge"

    save("record_name", record_name)

    print("Configuration completed! Thank you. Would you like to test renew now? (y/n)")
    do_test = input(">>> ")
    if do_test:
        new_txt_value = generate_certbot_cert(get.domain(), get.domain_email(), interactive=False)

        success = update_dns_txt(
            provider=provider,
            api_token=api_token,
            domain_name=get.domain(),
            record_name=record_name,
            txt_value=new_txt_value,
        )

        if success:
            print("DNS Updating successfully!")
        else:
            print("Somethings not right with updating the DNS. Check the token and data in settings and try again.")

def update_certbot_ssl():
    raise NotImplementedError

def generate_self_signed_cert(country_name, province_name, locality_name, organisation_name, common_name="localhost", valid_days=365):
    key_file, cert_file = get_ssl_filepaths()

    if os.path.exists("certs"):
        shutil.rmtree("certs", ignore_errors=True)
    os.makedirs(f"certs/config/live/{common_name}", exist_ok=True)

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

def setup_selfsigned():
    print("To setup SSL, we need to ask some questions.\n1. What's the base URL people will use to connect to this app on the web? (Default: localhost)")
    if not get.domain():
        common_name = input(">>> ")
        if not common_name:  # Entered nothing.
            common_name = "localhost"

        save("domain", common_name)
    else:
        common_name = get.domain()

    while True:
        print("2. What is the code for the name of your country? (Eg, 'US')")
        country_name = input(">>> ")
        if len(country_name) != 2:
            print("This must be a country code, eg, 'AU' or 'US', not a country name")
            continue
        break

    print("3. What is the name of your province? (Eg, 'California')")
    province_name = input(">>> ")

    print("4. What is your locality? (Eg, 'San Francisco')")
    locality_name = input(">>> ")

    print("5. What is your organisation name? (If you don't have one, leave it blank.)")
    organisation_name = input(">>> ")
    if not organisation_name:
        organisation_name = "N/A"
    
    os.makedirs('certs', exist_ok=True)
    generate_self_signed_cert(
        country_name=country_name,
        province_name=province_name,
        locality_name=locality_name,
        organisation_name=organisation_name,
        common_name=common_name,
        valid_days=365
    )

    # Remember the cert expires in 1 year
    one_yr_later = datetime.datetime.now() + datetime.timedelta(days=365)
    save("time_to_ssl_expiration", one_yr_later.timestamp())

    print("Warning: These certificates are self-signed. To get a trusted, free certificate, use cert bot.")

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
def route_prechecks(request: Request):
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

def __destroy_user_data(username: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        # Check they exist
        cur.execute("SELECT username FROM authbook WHERE username = ?", (username,))
        if not cur.fetchone():
            print("User not found.")
            return False

        # Get CFID if they have one
        cur.execute("SELECT cfid FROM cf_staff_usernames WHERE username = ?", (username,))
        row = cur.fetchone()
        cfid = row[0] if row else None

        # Username based tables
        username_tables = [
            ("auth_permissions", "username"),
            ("user_sessions", "username"),
            ("bulletin_archives", "owner"),
            ("finance_accounts", "owner"),
            ("battleplans", "owner"),
            ("bp_tasks", "owner"),
            ("bp_quotas", "owner"),
            ("odometer_entries", "user"),
        ]

        for table, column in username_tables:
            cur.execute(f"DELETE FROM {table} WHERE {column} = ?", (username,))

        # CFID Based tables
        if cfid is not None:
            cfid_tables = [
                "cf_names",
                "cf_name_types",
                "cf_ages",
                "cf_pronouns",
                "cf_profile_notes",
                "cf_pc_contact_details",
                "cf_is_dianetics_pc",
                "cf_dn_stuck_case",
                "cf_dn_control_case",
                "cf_dn_shutoffs",
                "cf_dn_fabricator_case",
                "cf_dn_action_records",
                "cf_tonescale_records",
                "cf_pc_mind_class",
                "cf_profile_images",
                "cf_occupations",
                "cf_dates_of_birth",
                "cf_pc_theta_endowments",
                "cf_pc_can_handle_life",
                "cf_agreements",
                "sessions_list",
                "session_actions",
                "session_engrams",
                "cf_chem_assist",
                "dn_schedule_data",
                "dn_scheduling_data_repeating",
                "cf_dynamic_strengths",
                "CF_hubbard_chard_of_eval",
            ]

            for table in cfid_tables:
                cur.execute(f"DELETE FROM {table} WHERE cfid = ?", (cfid,))

        # Remove auth records
        cur.execute("DELETE FROM authbook WHERE username = ?", (username,))
        cur.execute("DELETE FROM cf_staff_usernames WHERE username = ?", (username,))

        conn.commit()
        return True
    except sqlite3.OperationalError as err:
        conn.rollback()
        logbook.error("Error deleting a user's data.", err)
        return False
    finally:
        conn.close()

# -----------------------------
# Errors
# -----------------------------
class autherrors:
    class InvalidPassword(Exception):
        def __init__(self):
            pass
    class UserNotFound(Exception):
        def __init__(self):
            pass
    class ExistingUser(Exception):
        def __init__(self, username):
            self.username = username
    class AccountArrested(Exception):
        def __init__(self):
            pass

# -----------------------------
# Authbook
# -----------------------------
class authtype:
    class token:
        def __init__(self, token):
            self.token = str(token)
        def __str__(self):
            return str(self.token)
    class password:
        def __init__(self, password):
            self.password = str(password)
        def __str__(self):
            return str(self.password)

class authbook:
    class user_account:
        def __init__(self, username:str, authentication: authtype.password | authtype.token = None):
            self.username = username
            self.assosciated_cfid = self.get_assosciated_cfid()

            if isinstance(authentication, authtype.password):
                if not authbook.check_password(self.username, str(authentication)):
                    raise autherrors.InvalidPassword
            elif isinstance(authentication, authtype.token):
                if not authbook.verify_token(str(authentication)):
                    raise autherrors.InvalidPassword

        class errors:
            class nonconfirmation(Exception):
                pass

        def get_assosciated_cfid(self):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT cfid FROM cf_staff_usernames WHERE username = ?", (self.username,))
                row = cur.fetchone()
            cfid = row[0] if row else None 
            return cfid

        def delete(self, confirm:bool):
            if not confirm:
                raise self.errors.nonconfirmation
            
            success = __destroy_user_data(self.username)

            return success

        def get_is_admin(self):
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT admin FROM authbook WHERE username = ?",
                        (self.username,)
                    )
                    row = cur.fetchone()
                    if row:
                        return bool(row[0])
                    else:
                        return False
            except sqlite3.OperationalError as err:
                logbook.error(f"Error fetching if {self.username} is an admin", err)
                return False

        def get_is_arrested(self):
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT arrested FROM authbook WHERE username = ?",
                        (self.username,)
                    )
                    row = cur.fetchone()
                    if row:
                        return bool(row[0])
                    else:
                        return False
            except sqlite3.OperationalError as err:
                logbook.error(f"Error fetching if {self.username} is arrested", err)
                return False

    @staticmethod
    def check_exists(cfid:int=None, username:str=None):
        if cfid and username:
            raise ValueError("Pick one argument or the other, not both.")
        if not cfid and not username:
            raise ValueError("Too few arguments picked! Pick one or the other!")

        if cfid:
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT username FROM cf_staff_usernames WHERE cfid = ?",
                        (cfid,)
                    )
                    row = cur.fetchone()
                    return row is not None
            except sqlite3.Error as err:
                logbook.error("Database error fetching if user exists", exception=err)
                return False

        if username:
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT admin FROM authbook WHERE username = ?",
                        (username,)
                    )
                    row = cur.fetchone()
                    return row is not None
            except sqlite3.Error as err:
                logbook.error("Database error fetching if user exists", exception=err)
                return None

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

                # Create a CF Entry for the staff member too
                from modules.centralfiles.routes import centralfiles
                cfid = centralfiles.add_name(username)

                # Assosciate CFID with profile
                cur.execute(
                    "INSERT INTO cf_staff_usernames (cfid, username) VALUES (?, ?)",
                    (cfid, username),
                )

                return True
        except sqlite3.IntegrityError as err:
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
                    (str(token), datetime.datetime.now())
                )
                row = cur.fetchone()
                if not row:
                    return None

                cur.execute("SELECT 1 FROM revoked_tokens WHERE token = ?", (str(token),))
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
        """
        Checks if a token is valid, returns False if not.
        """
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
                raise autherrors.UserNotFound
            self.password = None
        else:
            self.username = details["username"].strip()
            self.password = details["password"].strip()
            self.request_ip = details["request_ip"]

            if not authbook.check_password(self.username, self.password):
                raise autherrors.InvalidPassword

            self.token = self.gen_token()

        if authbook.check_arrested(self.username):
            flag_ip(details.get("request_ip"))
            raise autherrors.AccountArrested

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
