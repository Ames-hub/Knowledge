import re

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

JAIL_PATH = "ftp_user_files/"

os.makedirs(JAIL_PATH, exist_ok=True)

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

class delete_data(BaseModel):
    path: str

@router.post("/api/ftp/delete")
async def delete_ftp(request: Request, data: delete_data, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is deleting file/folder {data.path}.")
    file_path, jail_real = resolve_path(data.path)

    if os.path.commonpath([jail_real, file_path]) != jail_real:
        return JSONResponse({"success": False, "error": "Path escapes jail."}, status_code=400)

    if not os.path.exists(file_path):
        return JSONResponse({"success": False, "error": "File/folder not found."}, status_code=404)

    try:
        if os.path.isdir(file_path):
            import shutil
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

class rename_data(BaseModel):
    path: str
    new_name: str

def validate_path(path):
    is_valid = re.match(r"^[a-zA-Z0-9_\-. ]+$", path)
    if is_valid:
        return path
    else:
        raise ValueError("Invalid path.")

@router.post("/api/ftp/rename")
async def rename_ftp(request: Request, data: rename_data, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is renaming file/folder {data.path} to {data.new_name}.")
    file_path, jail_real = resolve_path(data.path)

    if os.path.commonpath([jail_real, file_path]) != jail_real:
        return JSONResponse({"success": False, "error": "Path escapes jail."}, status_code=400)

    if not os.path.exists(file_path):
        return JSONResponse({"success": False, "error": "File/folder not found."}, status_code=404)

    # Verify it's a valid file name
    data.new_name = validate_path(data.new_name)

    new_path = os.path.join(os.path.dirname(file_path), data.new_name)
    try:
        os.rename(file_path, new_path)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

class mk_folder_data(BaseModel):
    path: str
    name: str

@router.post("/api/ftp/create-folder")
async def create_folder(request: Request, data: mk_folder_data, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is creating folder {data.path}.")
    file_path, jail_real = resolve_path(data.path)

    if os.path.commonpath([jail_real, file_path]) != jail_real:
        return JSONResponse({"success": False, "error": "Path escapes jail."}, status_code=400)
    if not os.path.exists(os.path.dirname(file_path)):
        return JSONResponse({"success": False, "error": "Directory not found."}, status_code=404)

    try:
        os.mkdir(os.path.join(file_path, data.name))
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

class mk_file_data(BaseModel):
    path: str
    name: str

@router.post("/api/ftp/create-file")
async def create_file(request: Request, data: mk_file_data, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is creating file {data.path}.")
    file_path, jail_real = resolve_path(data.path)

    if os.path.commonpath([jail_real, file_path]) != jail_real:
        return JSONResponse({"success": False, "error": "Path escapes jail."}, status_code=400)
    if not os.path.exists(os.path.dirname(file_path)):
        return JSONResponse({"success": False, "error": "folder not found."}, status_code=404)

    try:
        with open(os.path.join(file_path, data.name), "w") as f:
            f.write("")
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

class read_file_data(BaseModel):
    path: str

@router.post("/api/ftp/read-file")
async def read_file(request: Request, data: read_file_data, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is reading file {data.path}.")
    file_path, jail_real = resolve_path(data.path)

    if os.path.commonpath([jail_real, file_path]) != jail_real:
        return JSONResponse({"success": False, "error": "Path escapes jail."}, status_code=400)
    if not os.path.exists(file_path):
        return JSONResponse({"success": False, "error": "File not found."}, status_code=404)

    try:
        with open(file_path, "r") as f:
            content = f.read()
        return JSONResponse({"success": True, "content": content})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

class save_file_data(BaseModel):
    path: str
    content: str

@router.post("/api/ftp/save")
async def save_file(request: Request, data: save_file_data, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} (user: {authbook.token_owner(token)}) is the saving file {data.path}.")
    file_path, jail_real = resolve_path(data.path)

    if os.path.commonpath([jail_real, file_path]) != jail_real:
        return JSONResponse({"success": False, "error": "Path escapes jail."}, status_code=400)
    if not os.path.exists(os.path.dirname(file_path)):
        return JSONResponse({"success": False, "error": "Directory not found."}, status_code=404)

    try:
        with open(file_path, "w") as f:
            f.write(data.content)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)