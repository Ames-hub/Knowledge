from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.authperms import set_permission
from library.auth import require_prechecks
from library.logbook import LogBookHandler
from fastapi.responses import JSONResponse
from library.database import DB_PATH
from library.auth import authbook
from pydantic import BaseModel
import sqlite3
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("Textbook")

class SavePDFRequestWithID(BaseModel):
    archive_id: int | None = None
    title: str
    content: str
    tags: list

class LoadRequest(BaseModel):
    id: int

def check_archive_exists(archive_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM bulletin_archives WHERE archive_id = ?",
            (archive_id,)
        )
        return cursor.fetchone() is not None

@router.get("/textbook")
@set_permission(permission="bulletin_archives")
async def load_index(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) has accessed the bulletins / tech memory section.")
    return templates.TemplateResponse("index.html", {"request": request})

# TODO: Need to change all "archive" to "textbook" later on.
@set_permission(permission="bulletin_archives")
@router.post("/api/archives/save")
async def save_pdf(request: Request, data: SavePDFRequestWithID, token: str = Depends(require_prechecks)):
    logged_user = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({logged_user}) is saving a PDF to the archives.")

    parsed_tags = ",".join(data.tags)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if data.archive_id is not None:
            # Update the existing archive
            cursor.execute(
                """
                UPDATE bulletin_archives
                SET title = ?, content = ?, tags = ?
                WHERE archive_id = ? AND owner = ?
                """,
                (data.title, data.content, parsed_tags, data.archive_id, logged_user)
            )
            archive_id = data.archive_id
        else:
            # Insert a new archive
            cursor.execute(
                """
                INSERT INTO bulletin_archives (title, content, owner, tags)
                VALUES (?, ?, ?, ?)
                """,
                (data.title, data.content, logged_user, parsed_tags)
            )
            archive_id = cursor.lastrowid  # get new ID

    conn.commit()
    return JSONResponse(content={"message": "PDF saved successfully.", "archive_id": archive_id})

@set_permission(permission="bulletin_archives")
@router.post("/api/archives/delete")
async def del_pdf(data: LoadRequest, request: Request, token: str = Depends(require_prechecks)):
    logged_user = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({logged_user}) is deleting archive ID {data.id}.")

    if check_archive_exists(data.id) is False:
        return JSONResponse(content={"message": None, "error": "Archive not found.", "success": False}, status_code=404)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM bulletin_archives WHERE archive_id = ? AND owner = ?",
            (data.id, logged_user)
        )
        conn.commit()
        return JSONResponse(content={"message": "PDF deleted successfully.", "error": None, "success": True}, status_code=200)

@set_permission(permission="bulletin_archives")
@router.get("/api/archives/get_all")
async def get_all_pdfs(request: Request, token: str = Depends(require_prechecks)):
    logged_user = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({logged_user}) requested all PDF names in the archives.")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, tags, archive_id FROM bulletin_archives WHERE owner = ?",
            (logged_user,)
        )
        data = cursor.fetchall()

    pdfs = []
    tags_and_names = {}
    for title, tags, archive_id in data:
        parsed_tags = tags.split(" ")
        pdfs.append({
            "title": title,
            "tags": parsed_tags,
            "id": archive_id
        })
        tags_and_names[title] = tags

    return JSONResponse(
        content={
            "pdfs": pdfs,
            "tags_crossref": tags_and_names
        },
        status_code=200
    )

@set_permission(permission="bulletin_archives")
@router.post("/api/archives/load")
async def load_pdf(data: LoadRequest, request: Request, token: str = Depends(require_prechecks)):
    logged_user = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host} ({logged_user}) is loading archive ID {data.id}.")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, content, tags FROM bulletin_archives WHERE archive_id = ? AND owner = ?",
            (data.id, logged_user)
        )
        row = cursor.fetchone()

    if row:
        parsed_tags = row[2].split(" ")
        return JSONResponse(
            content={
                "title": row[0],
                "content": row[1],
                "tags": parsed_tags
            },
            status_code=200
        )
    else:
        return JSONResponse(
            content={"error": "Archive not found."},
            status_code=404
        )
