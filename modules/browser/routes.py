from library.auth import route_prechecks, authbook, authtype
from modules.centralfiles.routes import centralfiles
from library.modules import list_all_privelliged
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from library.logbook import LogBookHandler
from datetime import datetime, timedelta
from fastapi import APIRouter, Request
from library.settings import get
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("browser routes")

@router.get("/apps", response_class=HTMLResponse)
async def show_apps(request: Request):
    token = route_prechecks(request)
    owner = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} (user: {owner}) has accessed the app browser.")

    MODULES = list_all_privelliged(owner)

    enabled_modules = sorted(
        [m for m in MODULES.values() if m.get("enabled")],
        key=lambda m: m.get("order", 0)
    )

    user = authbook.user_account(owner, authtype.token(token))
    expiration_date = get.time_to_ssl_expiration()
    do_warn_user = (expiration_date - timedelta(days=7) <= datetime.now()) and user.get_is_admin()

    # Save some computational power
    if do_warn_user:
        time_left = expiration_date - datetime.now()
        relative_time = f"{time_left.days} day(s)"
        warn_msg = expiration_date.strftime(f"SSL Is going to expire in {relative_time}, on %d %b %Y at %I:%M %p")
    else:
        warn_msg = ""

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "modules": enabled_modules,
            "ssl_expiration_msg": warn_msg,
            "do_warn_expiration": do_warn_user,
            "profile": centralfiles.get_profile(cfid=user.assosciated_cfid)
        }
    )
