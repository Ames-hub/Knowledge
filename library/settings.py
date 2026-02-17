from library.logbook import LogBookHandler
from library.encryption import encryption
from datetime import datetime
import json
import os

# Super simple settings system.

logbook = LogBookHandler("settings")
SETTINGS_PATH = "settings.json"
keys = encryption("certs/encryption.key")

valid_settings = {
    "new_week_stats_plan": True,
    "weekday_end": 1,
    "registration_allowed": True,
    "lookback_length": 365,
    "use_ssl": False,
    "web_port": 8020,
    "route_perms": {},
    "debts_overpay_payback_tracking": True,  # If someone overpays a debt, log a new debt for the original debtee to pay back the overpaid amount.
    "do_bot_identification": True,
    "domain": None,
    "time_to_ssl_expiration": None,  #  timestamp
    "dns_provider": None,
    "dns_token": None,
    "record_name": None,
    "domain_email": None,
    "system_email": None,
    "sys_email_password": None
}

def make_settings_file():
    with open(SETTINGS_PATH, "w") as f:
        json.dump(valid_settings, f, indent=4, separators=(",", ": "))

class groupget:
    @staticmethod
    def all():
        return {
            "use_ssl": get.use_ssl(),
            "reset_bp_plan_on_new_week": get.reset_bp_plan_on_new_week(),
            "weekday_end": get.weekday_end(),
            "allow_registration": get.allow_registration(),
            "lookback_length": get.lookback_length(),
            "web_port": get.web_port(),
            "debts_overpay_payback_tracking": get.debts_overpay_payback_tracking(),
            "do_bot_identification": get.do_bot_identification(),
            "domain": get.domain(),
            "time_to_ssl_expiration": get.time_to_ssl_expiration(json_compat=True),
            "dns_provider": get.dns_provider(),
            "dns_token": get.dns_token(),
            "record_name": get.record_name(),
            "domain_email": get.domain_email(),
            "system_email": get.system_email(),
            "sys_email_password": get.sys_email_password(),
        }

class get:
    @staticmethod
    def get(key, default=None):
        if not os.path.exists(SETTINGS_PATH):
            return default
        with open(SETTINGS_PATH, "r") as f:
            settings = json.load(f)
            return settings.get(key, default)

    @staticmethod
    def use_ssl():
        return bool(get.get("use_ssl", False))

    @staticmethod
    def reset_bp_plan_on_new_week():
        return bool(get.get("new_week_stats_plan", False))

    @staticmethod
    def weekday_end():
        """
        1 = Monday
        2 = Tuesday
        3 = Wednesday
        4 = Thursday
        5 = Friday
        6 = Saturday
        7 = Sunday
        """
        return int(get.get("weekday_end", 1))

    @staticmethod
    def allow_registration():
        return bool(get.get("registration_allowed", True))

    @staticmethod
    def lookback_length():
        return int(get.get("lookback_length", 30))
    
    @staticmethod
    def web_port():
        return int(get.get("web_port", 8020))
    
    @staticmethod
    def debts_overpay_payback_tracking():
        return bool(get.get("debts_overpay_payback_tracking", True))

    @staticmethod
    def do_bot_identification():
        return bool(get.get("do_bot_identification", True))

    @staticmethod
    def domain():
        return str(get.get("domain", None))

    @staticmethod
    def time_to_ssl_expiration(json_compat:bool=False) -> datetime:
        data = get.get('time_to_ssl_expiration', datetime.now().timestamp())
        if not json_compat:
            expiration = datetime.fromtimestamp(float(data))
        else:
            return data
        return expiration
    
    @staticmethod
    def dns_provider():
        return str(get.get("dns_provider", None))

    @staticmethod
    def dns_token():
        data = get.get("dns_token", None)
        if data:
            return keys.decrypt(data)
        else:
            return data

    @staticmethod
    def record_name():
        return str(get.get("record_name", None))

    # The one used to register domains.
    @staticmethod
    def domain_email():
        data = get.get("domain_email", None)
        if data:
            return keys.decrypt(data)
        else:
            return data    

    # The one used to send emails.
    @staticmethod
    def system_email():
        data = get.get("system_email", None)
        if data:
            return keys.decrypt(data)
        else:
            return data

    @staticmethod
    def sys_email_password():
        data = get.get("sys_email_password", None)
        if data:
            return keys.decrypt(data)
        else:
            return data

class set:
    def set(key:str, value, encrypt:bool=False) -> bool:
        if key not in valid_settings.keys():
            raise KeyError("This is a bad key for settings!")

        if key == "allow_registration":
            value = bool(value)
        
        with open(SETTINGS_PATH, "r") as f:
            data = json.load(f)

        if not encrypt:
            data[key] = value
        else:
            if type(value) is str:
                data[key] = keys.encrypt(value)
            else:
                data[key] = value

        with open(SETTINGS_PATH, "w") as f:
            json.dump(data, f, indent=4)
        
        return True
    
    def use_ssl(value:bool):
        return set.set("use_ssl", bool(value))
    def reset_bp_plan_on_new_week(value:bool):
        return set.set("reset_bp_plan_on_new_week", bool(value))
    def weekday_end(value:str):
        ref_dict = {
            "monday": 1,
            "tuesday": 2,
            "wednesday": 3,
            "thursday": 4,
            "friday": 5,
            "saturday": 6,
            "sunday": 7,
        }
        value = ref_dict.get(value.lower(), 1)
        return set.set("weekday_end", value)
    def allow_registration(value:bool):
        return set.set("allow_registration", bool(value))
    def lookback_length(value:int):
        return set.set("lookback_length", int(value))
    def web_port(value:int):
        return set.set("web_port", int(value))
    def debts_overpay_payback_tracking(value:bool):
        return set.set("debts_overpay_payback_tracking", bool(value))
    def do_bot_identification(value:bool):
        return set.set("do_bot_identification", bool(value))
    def domain(value:str):
        return set.set("domain", value)
    def time_to_ssl_expiration(value):
        return set.set("time_to_ssl_expiration", value)
    def dns_provider(value:str):
        return set.set("dns_provider", str(value))
    def dns_token(value:str):
        return set.set("dns_token", str(value), encrypt=True)
    def record_name(value:str):
        return set.set("record_name", str(value))
    # The one used to register domains.
    def domain_email(value:str):
        return set.set("domain_email", str(value), encrypt=True)
    # The one used to send emails.
    def system_email(value:str):
        return set.set("system_email", str(value), encrypt=True)
    def sys_email_password(value:str):
        return set.set("sys_email_password", str(value), encrypt=True)