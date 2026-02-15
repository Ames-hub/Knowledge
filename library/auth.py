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
import requests
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
    key_file = f"certs/config/live/{domain}/privkey.pem"
    cert_file = f"certs/config/live/{domain}/fullchain.pem"
    return key_file, cert_file

# -----------------------------
# Certificates
# -----------------------------
def update_dns_txt(provider: str, api_token: str, domain_name: str, record_name: str, txt_value: str) -> bool:
    """
    Create or update a TXT record for DNS-01 challenge on Cloudflare or Dynu.

    :param provider: "cloudflare" or "dynu"
    :param api_token: API token/key for the DNS provider
    :param domain_name: Domain/zone name, e.g., 'example.com'
    :param record_name: Full TXT record name, e.g., '_acme-challenge.example.com'
    :param txt_value: TXT value to set
    :return: True if successful, False otherwise
    """

    # TODO: Please someone test if the cloudflare updating works. I can't :')
    if provider.lower() == "cloudflare":
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        # 1. Get zone ID
        zones = requests.get(f"https://api.cloudflare.com/client/v4/zones?name={domain_name}", headers=headers).json()
        if not zones.get("result"):
            print("Cloudflare zone not found")
            return False
        zone_id = zones["result"][0]["id"]

        # 2. Check if TXT record exists
        records = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=TXT&name={record_name}", headers=headers).json()

        if records["result"]:
            record_id = records["result"][0]["id"]
            response = requests.put(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
                headers=headers,
                json={"type": "TXT", "name": record_name, "content": txt_value, "ttl": 120}
            )
        else:
            response = requests.post(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
                headers=headers,
                json={"type": "TXT", "name": record_name, "content": txt_value, "ttl": 120}
            )

        return response.ok

    elif provider.lower() == "dynu":
        headers = {
            "Api-Key": api_token,
            "Content-Type": "application/json"
        }

        # 1. Get domain ID
        domains = requests.get(f"https://api.dynu.com/v2/dns/{domain_name}", headers=headers).json()
        if "records" not in domains:
            print("Dynu zone not found")
            return False

        # 2. Look for existing TXT record
        record_id = None
        for record in domains["records"]:
            if record["name"] == record_name and record["type"] == "TXT":
                record_id = record["id"]
                break

        if record_id:
            response = requests.put(
                f"https://api.dynu.com/v2/dns/{domain_name}/records/{record_id}",
                headers=headers,
                json={"name": record_name, "type": "TXT", "data": txt_value, "ttl": 120}
            )
        else:
            response = requests.post(
                f"https://api.dynu.com/v2/dns/{domain_name}/records",
                headers=headers,
                json={"name": record_name, "type": "TXT", "data": txt_value, "ttl": 120}
            )

        return response.ok

    else:
        print("Unsupported provider")
        return False

def generate_certbot_cert(
    domain: str, 
    email: str, 
    auth_hook: str = None, 
    interactive: bool = True
) -> str | bool:
    """
    Generate a DNS-01 cert for a domain using Certbot.

    :param domain: Domain to generate cert for
    :param email: Your email
    :param auth_hook: Optional path to a hook script to auto-set TXT record
    :param interactive: If True, wait for manual "press Enter" to continue; if False, run non-interactively
    :return: TXT code for manual DNS if interactive=True and no hook, or True if successful with hook or non-interactive
    """
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
            "--config-dir", "./certs/config",
            "--work-dir", "./certs/work",
            "--logs-dir", "./certs/logs",
        ]

        if not interactive:
            cmd += ["--non-interactive", "--manual-public-ip-logging-ok"]

        if auth_hook:
            cmd += ["--manual-auth-hook", auth_hook, "--manual-cleanup-hook", auth_hook]

        # Run certbot and capture stdout/stderr
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logbook.info(f"Return code for setting up SSL with certbot: {result.returncode}")

        # Fix permissions
        os.chmod("certs", 0o755)

        # If no auth hook and interactive, parse TXT from Certbot output
        if interactive and not auth_hook:
            for line in result.stdout.splitlines():
                if "_acme-challenge" in line and "TXT value" in line:
                    txt_value = line.split("value:")[-1].strip()
                    return txt_value
            return False

        # Otherwise, just return True for success
        return True

    except subprocess.CalledProcessError as e:
        logbook.error(f"Certbot failed for domain {domain}: {e.stderr}")
        return False

def setup_certbot_ssl():
    print("What is the domain of your website for this certificate? eg, google.com")
    domain = input(">>> ")
    print("What's the email address you wish to use for the certificate?")
    email_address = input(">>> ")

    save("domain", domain)
    save("domain_email", email_address)

    success = generate_certbot_cert(
        domain=domain,
        email=email_address
    )
    print(f"SSL Setup success: {success}")
    if not success:
        print("Success failure. Defaulting to self-signed certs.")
        setup_selfsigned()

    print("Would you like to setup auto-renewing for the Certificates?")
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

        update_dns_txt(
            provider=provider,
            api_token=api_token,
            domain_name=get.domain(),
            record_name=record_name,
            txt_value=new_txt_value,
        )

def update_certbot_ssl():
    new_txt_value = generate_certbot_cert(get.domain(), get.domain_email(), interactive=False)
    success = update_dns_txt(
        provider=get.dns_provider(),
        api_token=get.dns_token(),
        domain_name=get.domain(),
        record_name=get.record_name(),
        txt_value=new_txt_value
    )
    return success

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
    
    os.makedirs('certs')
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

                # Create a CF Entry for the staff member too
                from modules.centralfiles.routes import centralfiles
                centralfiles.add_name(username)

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
