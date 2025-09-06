from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.auth import require_valid_token
from fastapi.responses import HTMLResponse
from library.logbook import LogBookHandler
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("browser routes")

# noinspection PyUnusedLocal
@router.get("/", response_class=HTMLResponse)
async def show_reg(request: Request, token: str = Depends(require_valid_token)):
    return templates.TemplateResponse(request, "index.html")