from fastapi.responses import HTMLResponse, JSONResponse
from library.auth import require_prechecks, authbook
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.authperms import set_permission
from library.logbook import LogBookHandler
from pydantic import BaseModel
from library import settings
import json
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("register")

@router.get("/knowledge", response_class=HTMLResponse)
@set_permission(permission="app_settings")
async def show_index(request: Request, token=Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is accessing the app settings page.")
    return templates.TemplateResponse(request, "settings.html")

class SettingsData(BaseModel):
    config: dict

@router.post("/api/settings/save")
@set_permission(permission="app_settings")
async def save_settings(request: Request, data: SettingsData, token=Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is saving settings. New config: {data.config}")
    for setting, value in data.config.items():
        setting = str(setting).lower()
        if setting not in settings.valid_settings.keys():
            return HTMLResponse(f"ERR: Setting key \"{setting}\" Invalid.", status_code=400)
        settings.save(
            key=setting,
            value=value,
        )
    return HTMLResponse(content="Settings saved successfully.", status_code=200)

@router.get("/api/settings/load")
@set_permission(permission="app_settings")
async def load_settings(request: Request, token=Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is loading settings.")
    with open('settings.json', 'r') as f:
        data = json.load(f)

    data['route_perms'] = ["You're not allowed to see this."]  # Hide it

    return JSONResponse(data)