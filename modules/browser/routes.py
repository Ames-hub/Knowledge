from library.auth import require_prechecks, authbook
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from library.logbook import LogBookHandler
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("browser routes")

@router.get("/apps", response_class=HTMLResponse)
async def show_apps(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the app browser.")
    return templates.TemplateResponse(request, "index.html")