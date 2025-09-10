from fastapi.responses import HTMLResponse, FileResponse
from library.auth import require_valid_token, authbook
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.logbook import LogBookHandler
from pydantic import BaseModel
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler('File Server')

JAIL_PATH = "modules/ftp/userfiles"

class walk_data(BaseModel):
    path: str

def resolve_path(path: str):
    """
    Resolve a requested path safely inside the jail.
    Returns (resolved_path, jail_real).
    Raises ValueError if invalid or outside jail.
    """
    if not os.path.exists(JAIL_PATH):
        raise FileNotFoundError("Jail path does not exist.")

    jail_real = os.path.realpath(JAIL_PATH)
    requested = (path or "").replace("\\", "/").lstrip("/")
    requested = os.path.normpath(requested)

    if requested.startswith(".."):
        raise ValueError("Invalid path.")

    resolved = os.path.realpath(os.path.join(jail_real, requested))
    if os.path.commonpath([jail_real, resolved]) != jail_real:
        raise ValueError("Path escapes jail.")

    return resolved, jail_real

def list_directory(path: str):
    """
    Return files and folders inside a directory.
    """
    all_files, all_folders = [], []
    with os.scandir(path) as entries:
        for entry in entries:
            if entry.is_file():
                all_files.append({
                    "name": entry.name,
                    "size": entry.stat().st_size
                })
            elif entry.is_dir():
                all_folders.append({"name": entry.name})
    return all_files, all_folders

@router.get("/ftp", response_class=HTMLResponse)
async def ftp(request: Request):
    return templates.TemplateResponse("ftp.html", {"request": request})

@router.post("/api/ftp/walk")
async def walk_ftp(request: Request, data: walk_data, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) accessed ftp dir {data.path}.")

    try:
        path, jail_real = resolve_path(data.path)
    except (FileNotFoundError, ValueError) as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=400)

    if not os.path.exists(path):
        return JSONResponse(content={"success": False, "error": "Path does not exist."}, status_code=404)

    all_files, all_folders = list_directory(path)

    # Relative path (to keep the client inside the jail namespace)
    rel_path = os.path.relpath(path, jail_real)
    if rel_path == ".":
        rel_path = ""

    return JSONResponse(
        content={"path": rel_path, "files": all_files, "folders": all_folders},
        status_code=200
    )

# Pydantic model for JSON part (metadata only)
class UploadMeta(BaseModel):
    path: str

from pydantic import BaseModel
from typing import List
import base64
import os
from fastapi.responses import JSONResponse
from fastapi import Request, Depends

class FileData(BaseModel):
    name: str
    data: str  # base64 string

class UploadData(BaseModel):
    path: str
    files: List[FileData] = []

@router.post("/api/ftp/upload")
async def upload_ftp(request: Request, data: UploadData, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is uploading files to {data.path}.")

    file_path, jail_real = resolve_path(data.path)
    if not os.path.exists(file_path):
        return JSONResponse(content={"success": False, "error": "Upload path does not exist."}, status_code=404)

    if os.path.commonpath([jail_real, file_path]) != jail_real:
        return JSONResponse(content={"success": False, "error": "Path escapes jail."}, status_code=400)

    saved_files = []
    for file in data.files:
        dest = os.path.join(file_path, file.name)
        with open(dest, "wb") as f:
            f.write(base64.b64decode(file.data))
        saved_files.append(file.name)

    return JSONResponse(content={"success": True, "files": saved_files}, status_code=200)

@router.get("/api/ftp/download")
async def download_ftp(request: Request, path: str, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) downloaded file {path}.")

    try:
        file_path, jail_real = resolve_path(path)
    except (FileNotFoundError, ValueError) as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=400)

    if not os.path.isfile(file_path):
        return JSONResponse(content={"success": False, "error": "File not found."}, status_code=404)

    return FileResponse(file_path, filename=os.path.basename(file_path))