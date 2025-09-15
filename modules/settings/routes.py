from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from library.logbook import LogBookHandler
from fastapi import APIRouter, Request
from pydantic import BaseModel
from library import settings
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("register")

@router.get("/settings", response_class=HTMLResponse)
async def show_index(request: Request):
    return templates.TemplateResponse(request, "settings.html")

class SettingsData(BaseModel):
    config: dict

@router.post("/api/settings/save")
async def save_settings(request: Request, data: SettingsData):
    logbook.info(f"IP {request.client.host} is saving settings. New config: {data.config}")
    for setting, value in data.config.items():
        settings.save(
            key=setting,
            value=value,
        )
    return HTMLResponse(content="Settings saved successfully.", status_code=200)