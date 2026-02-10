from library.authperms import AuthPerms
import json

JSON_MODULES_PATH = "modules.json"

# Non-Essential Only
VALID_MODULES = [
    'battleplans',
    'centralfiles',
    'ftp',
    'ledger',
    'logviewer',
    'signals',
    'textbook'
]

def list_all():
    with open(JSON_MODULES_PATH, "r") as f:
        data = json.load(f)
    return data

def list_all_privelliged(username):
    with open(JSON_MODULES_PATH, "r") as f:
        data = json.load(f)
    
    # Only return that which they're allowed to see
    final_data = {}
    for item_name in data:
        item = data[item_name]
        if item['display_perm'] in AuthPerms.perms_for_user(username):
            final_data[item_name] = item
    
    return final_data

def set_enabled(module, status:bool):
    if module not in VALID_MODULES:
        return False
    
    with open(JSON_MODULES_PATH, "w") as f:
        data = json.load(f)

    data[module]['enabled'] = bool(status)
    
    with open(JSON_MODULES_PATH, "w") as f:
        json.dump(data, f, separators=[",", ":"])

    return True