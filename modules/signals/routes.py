from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.authperms import set_permission
from library.auth import require_prechecks
from library.logbook import LogBookHandler
from library.database import DB_PATH
from library.auth import authbook
from pydantic import BaseModel
import importlib
import datetime
import sqlite3
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("Signal Server")

@router.get("/signals", response_class=HTMLResponse)
@set_permission(permission="signal_server")
async def show_page(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) has accessed the signal server.")
    return templates.TemplateResponse(
        request,
        "signals.html",
    )

def make_new_signal(route, http_code, html_response, route_func):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO signalserver_items (signal_route, http_code, html_response, route_func)
                VALUES (?, ?, ?, ?) 
                """,
                (route, http_code, html_response, route_func),
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as err:
            logbook.error(f"Could not create new signal: {err}", exception=err)
            conn.rollback()
            return False

class mk_signal_data(BaseModel):
    signal_route: str
    http_code: int
    html_response: str
    route_func: str

@router.post("/api/signals/mknew", response_class=HTMLResponse)
@set_permission(permission="signal_server")
async def mksignal(request: Request, signal: mk_signal_data, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) has made a new signal.")

    if "/" in signal.signal_route or "\\" in signal.signal_route:
        return HTMLResponse(
            "Incorrect formatting! Your route cannot have a slash.",
            status_code=400,
        )
    elif signal.signal_route.startswith('http'):
        return HTMLResponse(
            "Incorrect formatting! Your route starts from ...api/signals/r/(your_route). Do not add the HTTP stuff!",
            status_code=400,
        )

    success = make_new_signal(
        route=signal.signal_route,
        http_code=signal.http_code,
        html_response=signal.html_response,
        route_func=signal.route_func,
    )

    return HTMLResponse(
        "Success! New route created." if success else "Failed to create new route.",
        status_code=200 if success else 400,
    )

class SaveCodeSignalData(BaseModel):
    signal_route: str
    http_code: int

def save_signal_code(signal_route: str, http_code: int):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE signalserver_items SET http_code = ? WHERE signal_route = ?
                """,
                (http_code, signal_route),
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as err:
            conn.rollback()
            logbook.error(f"Error trying to save signal code as {http_code} for {signal_route} | {err}", exception=err)
            return False

@router.post("/api/signals/save/code")
@set_permission(permission="signal_server")
async def route_signalcode_save(request: Request, signal: SaveCodeSignalData, token=Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) has saved a signal for {signal.signal_route}.")

    success = save_signal_code(signal.signal_route, signal.http_code)

    return HTMLResponse(
        content="Success!" if success else "Failure! Couldn't save signal!",
        status_code=200 if success else 400,
    )

def save_html_response(signal_route: str, html_response: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE signalserver_items SET html_response = ? WHERE signal_route = ?
                """,
                (html_response, signal_route),
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as err:
            logbook.error(f"Error trying to save html response for {signal_route} | {err}", exception=err)
            conn.rollback()
            return False

class SaveSignalData(BaseModel):
    signal_route: str
    html_response: str

@router.post("/api/signals/save/html")
@set_permission(permission="signal_server")
async def route_save_html_response(request: Request, signal: SaveSignalData, token=Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) Has saved the HTML response for {signal.signal_route} as:\n{signal.html_response}\n")

    success = save_html_response(signal.signal_route, signal.html_response)

    return HTMLResponse(
        content="Success!" if success else "Failure! Couldn't save signal!",
        status_code=200 if success else 400,
    )

def get_route_response(route):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT http_code, html_response, route_func FROM signalserver_items WHERE signal_route = ?
                """,
                (route,)
            )
            data = cur.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Error trying to get route response for {route} | {err}", exception=err)
            conn.rollback()
            return None

    return {"http_code": data[0], "html_response": data[1], "route_func": data[2]} if data else None

def get_signals_list():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT signal_route, http_code, html_response, is_closed, route_func FROM signalserver_items
                """
            )
            data = cur.fetchall()
        except sqlite3.OperationalError as err:
            logbook.error(f"Error trying to get signals list | {err}", exception=err)
            return False

    sig_list = {}
    for route, http_code, html_response, is_closed, route_func in data:
        sig_list[route] = {
            "http_code": http_code,
            "html_response": html_response,
            "route": route,
            "closed": is_closed,
            "route_func": route_func,
        }
    return sig_list

def get_route_closed(route):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT is_closed FROM signalserver_items WHERE signal_route = ?
                """,
                (route,),
            )
            data = cur.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Failed to get if route \"{route}\" closed | {err}", exception=err)
            conn.rollback()
            return False

    return data[0] if data else None

@router.get("/api/signals/list")
@set_permission(permission="signal_server")
async def list_signals(request: Request, token=Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) has listed all routes.")

    data = get_signals_list()
    return JSONResponse(
        content=data,
        status_code=200,
    )

class loadSignalData(BaseModel):
    signal_route: str

@router.post("/api/signals/load")
@set_permission(permission="signal_server")
async def load_signal(request: Request, signal: loadSignalData, token=Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) has loaded the signal {signal.signal_route}.")

    data = get_signals_list().get(signal.signal_route, None)

    if not data:
        return JSONResponse(
            content={"message": "No route was found"},
            status_code=404,
        )
    return JSONResponse(
        content=data,
        status_code=200,
    )


def parse_placeholders(html_response:str, func_response:str="") -> str:
    """
    To add logical data to your HTML response, you need to modify this function.
    """
    logical_data_map = {
        "<date>": datetime.datetime.now().strftime("%m/%d/%Y"),
        "<time>": datetime.datetime.now().strftime("%H:%M:%S"),
        "<func_response>": func_response,
    }
    for key in logical_data_map:
        html_response = html_response.replace(key, logical_data_map[key])
    return html_response

@router.get("/api/signals/r/{signal_route}")
async def read_route(request: Request, signal_route):
    logbook.info(f"IP {request.client.host} Is accessing signal route \"{signal_route}\"")

    route_data = get_route_response(signal_route)

    if not route_data:
        return HTMLResponse(
            content="Route not found!",
        )
    
    route_func = route_data["route_func"]
    func_file_path = os.path.join("modules", "signals", "route_funcs", f"{route_func.replace(".", "/")}.py")

    func_response = "NO_FUNCTION_RESPONSE"
    func_code = None
    if os.path.exists(func_file_path):
        try:
            route_module = importlib.import_module(f"modules.signals.route_funcs.{route_func}")
            if hasattr(route_module, "main"):
                func_data = route_module.main()
                func_response = func_data[0]
                if len(func_data) > 1:
                    func_code = func_data[1]
                else:
                    func_code = None
        except Exception as err:
            logbook.error(f"Error executing route function {route_func} for route {signal_route} | {err}", exception=err)
            return HTMLResponse(
                content="Internal Server Error while executing user-generated route function.",
                status_code=500
            )

    if get_route_closed(signal_route):
        return HTMLResponse(
            content=f"Route {signal_route} is closed.",
            status_code=401
        )

    html_response = parse_placeholders(route_data["html_response"], func_response=func_response)

    return HTMLResponse(content=html_response, status_code=route_data["http_code"] if func_code is None else func_code)

def del_route(route):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                DELETE FROM signalserver_items WHERE signal_route = ?
                """,
                (route,),
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as err:
            logbook.error(f"Failed to delete route \"{route}\" | {err}", exception=err)
            conn.rollback()
            return False

class del_data(BaseModel):
    signal_route: str

@router.post("/api/signals/delete")
@set_permission(permission="signal_server")
async def delete_route(request: Request, data: del_data, token=Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) Is deleting route \"{data.signal_route}\"")
    success = del_route(data.signal_route)
    return HTMLResponse(
        content="Deleted!" if success else "Failed to delete!",
        status_code=200 if success else 500,
    )

def close_route(signal_route):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE signalserver_items SET is_closed = ? WHERE signal_route = ?
                """,
                (True, signal_route),
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as err:
            logbook.error(f"Failed to close route \"{signal_route}\" | {err}", exception=err)
            conn.rollback()
            return False

@router.post("/api/signals/close/{signal_route}")
@set_permission(permission="signal_server")
async def route_close_route(request: Request, signal_route, token=Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)} Closing route \"{signal_route}\"")

    success = close_route(signal_route)

    return HTMLResponse(
        content="Closed!" if success else "Failed to close!",
        status_code=200 if success else 500,
    )

def open_route(signal_route):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE signalserver_items SET is_closed = ? WHERE signal_route = ?
                """,
                (False, signal_route),
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as err:
            logbook.error(f"Failed to open route \"{signal_route}\" | {err}", exception=err)
            conn.rollback()
            return False

@router.post("/api/signals/open/{signal_route}")
@set_permission(permission="signal_server")
async def route_open_route(request: Request, signal_route, token=Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)} opening route \"{signal_route}\"")

    success = open_route(signal_route)

    return HTMLResponse(
        content="Opened!" if success else "Failed to open!",
        status_code=200 if success else 500,
    )