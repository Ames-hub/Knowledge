from fastapi.responses import HTMLResponse, JSONResponse
from library.auth import authbook, UserLogin, autherrors
from fastapi.templating import Jinja2Templates
from library.logbook import LogBookHandler
from fastapi import APIRouter, Request
from pydantic import BaseModel
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler('login routes')

class TokenData(BaseModel):
    token: str

class LoginData(BaseModel):
    username: str
    password: str

@router.get("/login", response_class=HTMLResponse)
async def show_login(request: Request):
    logbook.info(f"IP {request.client.host} accessed the login page.")
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/api/token/check")
async def verify_token(request: Request, data: TokenData):
    verified = authbook.verify_token(data.token)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(data.token)}) has attempted to verify their token.")
    return JSONResponse(content={'verified': verified}, status_code=200 if verified else 401)

@router.post("/api/user/login")
async def login_user(request: Request, data: LoginData):
    # Generates a key and returns it if it's okay.
    try:
        user = UserLogin(details={
            "username": data.username,
            "password": data.password,
            "request_ip": request.client.host
        })
    except autherrors.UserNotFound:
        logbook.info(f"Under the IP {request.client.host}, Non-Existent user {data.username} attempted to log in unsuccessfully.")
        return JSONResponse(content="An account with that username does not exist.", status_code=404)
    except (autherrors.InvalidPassword, autherrors.AccountArrested) as err:
        logbook.info(f"Under the IP {request.client.host}, user {data.username} attempted to log in unsuccessfully.")
        return JSONResponse(content={'error': str(err)}, status_code=401)

    data = {'token': user.token}
    if user.logged_via_forcekey:
        data['forced'] = True

    return JSONResponse(
        content=data,
        status_code=200
    )