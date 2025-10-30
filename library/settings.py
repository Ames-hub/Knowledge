from library.logbook import LogBookHandler
import json
import os

# Super simple settings system.

logbook = LogBookHandler("settings")
SETTINGS_PATH = "settings.json"

valid_settings = {
    "new_week_stats_plan": True,
    "weekday_end": 1,
    "registration_allowed": True,
    "lookback_length": 7,
    "use_ssl": False,
}

def make_settings_file():
    with open(SETTINGS_PATH, "w") as f:
        json.dump(valid_settings, f, indent=4, separators=(",", ": "))

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

def save(key, value):
    settings = {}

    if key not in valid_settings.keys():
        raise KeyError("This is a bad key for settings!")

    if key == "allow_registration":
        value = bool(value)
    elif key == "weekday_end":
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

    # Load existing settings if a file exists
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                logbook.warning("Settings file was corrupted. Overwriting.")

    logbook.info(f"Saving setting '{key}' with value '{value}'")
    settings[key] = value

    # Write back updated settings
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=4)

    return True
