from library.auth import require_prechecks, authbook
from library.modules import list_all_privelliged
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
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} (user: {owner}) has accessed the app browser.")

    MODULES = list_all_privelliged(owner)

    enabled_modules = sorted(
        [m for m in MODULES.values() if m.get("enabled")],
        key=lambda m: m.get("order", 0)
    )

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "modules": enabled_modules}
    )
