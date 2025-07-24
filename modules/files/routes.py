from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.auth import require_valid_token
from fastapi.responses import HTMLResponse
from library.logbook import LogBookHandler
from fastapi.responses import JSONResponse
from library.database import DB_PATH
from library.auth import authbook
from pydantic import BaseModel
import datetime
import sqlite3
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("Central Files")

class NamePostData(BaseModel):
    name: str

class LoginData(BaseModel):
    username: str

class ModifyFileData(BaseModel):
    cfid: int
    field: str
    value: str

class NoteData(BaseModel):
    note_id: int
    note: str

class NoteDeleteData(BaseModel):
    note_id: int

class NoteCreateData(BaseModel):
    cfid: int
    note: str

class DeleteNameData(BaseModel):
    name: str

class centralfiles:
    class errors:
        class TooManyProfiles(Exception):
            def __init__(self):
                self.message = "Too Many Profiles"

            def __str__(self):
                return self.message

        class ProfileNotFound(Exception):
            def __init__(self):
                self.message = "Profile Not Found"

            def __str__(self):
                return self.message

    class modify:
        def __init__(self, cfid):
            self.cfid = int(cfid)

        def name(self, new_name):
            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO cf_names (cfid, name) VALUES (?, ?)
                    ON CONFLICT(cfid) DO UPDATE SET name=excluded.name
                    """,
                    (self.cfid, new_name)
                )
                conn.commit()
                return True
            except sqlite3.OperationalError:
                conn.rollback()
                return False
            finally:
                conn.close()

        def age(self, new_age):
            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO cf_ages (cfid, age) VALUES (?, ?)
                    ON CONFLICT(cfid) DO UPDATE SET age=excluded.age
                    """,
                    (self.cfid, int(new_age))
                )
                conn.commit()
                return True
            except sqlite3.OperationalError:
                conn.rollback()
                return False
            finally:
                conn.close()

        def pronouns(self, subjective, objective):
            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO cf_pronouns (cfid, subjective, objective) VALUES (?, ?, ?)
                    ON CONFLICT(cfid) DO UPDATE SET subjective=excluded.subjective, objective=excluded.objective
                    """,
                    (self.cfid, subjective, objective)
                )
                conn.commit()
                return True
            except sqlite3.OperationalError:
                conn.rollback()
                return False
            finally:
                conn.close()

    class notes:
        def __init__(self, note_id):
            self.note_id = int(note_id)

        @staticmethod
        def create(cfid, note, author):
            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO cf_profile_notes (cfid, note, author) VALUES (?, ?, ?)
                    """,
                    (cfid, note, author)
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.OperationalError:
                conn.rollback()
                return None
            finally:
                conn.close()

        def modify(self, new_note):
            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE cf_profile_notes SET note = ? WHERE note_id = ?",
                    (str(new_note), self.note_id)
                )
                conn.commit()
                return True
            except sqlite3.OperationalError:
                conn.rollback()
                return False
            finally:
                conn.close()

        def delete(self):
            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM cf_profile_notes WHERE note_id = ?",
                    (self.note_id,)
                )
                conn.commit()
                return True
            except sqlite3.OperationalError:
                conn.rollback()
                return False
            finally:
                conn.close()

    @staticmethod
    def add_name(name):
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO cf_names (name) VALUES (?)
                """,
                (name,),
            )
            cfid = cursor.lastrowid
            # Inserts into the other fields some data
            cursor.execute(
                "INSERT INTO cf_ages (cfid, age) VALUES (?, ?)",
                (cfid, -1)
            )
            cursor.execute(
                "INSERT INTO cf_pronouns (cfid, subjective, objective) VALUES (?, ?, ?)",
                (cfid, "UNK", "UNK")
            )

            conn.commit()
            return cfid
        except sqlite3.OperationalError:
            conn.rollback()
        finally:
            conn.close()

    @staticmethod
    def delete_name(name):
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM cf_names WHERE name = ?",
                (name,),
            )
            conn.commit()
            # Returns True if any row deleted
            return cursor.rowcount > 0
        except sqlite3.OperationalError:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def get_names():
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, cfid FROM cf_names ORDER BY name ASC"
            )
            data = cursor.fetchall()

            parsed_names = []
            parsed_cfids = []
            for item in data:
                parsed_names.append(item[0])
                parsed_cfids.append(item[1])

            return parsed_names, parsed_cfids
        except sqlite3.OperationalError:
            conn.rollback()
        finally:
            conn.close()

    @staticmethod
    def get_profile(name=None, cfid=None):
        if name is None and cfid is None:
            raise ValueError("Name and CFID cannot both be None!")

        conn = sqlite3.connect(DB_PATH)

        try:
            cursor = conn.cursor()
            if cfid is None:
                cursor.execute(
                    "SELECT cfid, name FROM cf_names WHERE name = ?",
                    (name,),
                )
                data = cursor.fetchall()
                if len(data) != 1:
                    raise centralfiles.errors.TooManyProfiles()
                else:
                    cfid = data[0][0]
                    name = data[0][1]
            else:
                cursor.execute(
                    "SELECT cfid, name FROM cf_names WHERE cfid = ?",
                    (cfid,),
                )
                data = cursor.fetchone()
                cfid = data[0]
                name = data[1]

            cfid = int(cfid)
            name = str(name)

            # Gets the age, pronouns, and all case notes.
            cursor.execute(
                """
                SELECT age from cf_ages WHERE cfid = ?
                """,
                (cfid,),
            )
            age = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT subjective, objective FROM cf_pronouns WHERE cfid = ?
                """,
                (cfid,),
            )
            data = cursor.fetchone()
            subject_pron = data[0]
            objective_pron = data[1]

            cursor.execute(
                """
                SELECT note_id, note, add_date, author FROM cf_profile_notes WHERE cfid = ?
                """,
                (cfid,),
            )
            data = cursor.fetchall()
            profile_notes = {}
            for item in data:
                note_id = item[0]
                profile_notes[note_id] = {
                    "note": item[1],
                    "add_date": item[2],
                    "author": item[3],
                }

            profile = {
                "cfid": cfid,
                "name": name,
                "age": age,
                "pronouns": {
                    "subject_pron": subject_pron,
                    "objective_pron": objective_pron,
                },
                "profile_notes": profile_notes,
            }

            return profile
        except TypeError:
            raise centralfiles.errors.ProfileNotFound()
        finally:
            conn.close()

    @staticmethod
    def get_all_profiles():
        conn = sqlite3.connect(DB_PATH)

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT cfid, name FROM cf_names")
            rows = cursor.fetchall()

            all_profiles = []

            for cfid, name in rows:
                profile = {
                    "cfid": cfid,
                    "name": name,
                    "age": None,
                    "pronouns": {
                        "subject_pron": None,
                        "objective_pron": None,
                    },
                    "profile_notes": {},
                }

                # Get age
                cursor.execute("SELECT age FROM cf_ages WHERE cfid = ?", (cfid,))
                age_data = cursor.fetchone()
                if age_data:
                    profile["age"] = age_data[0]

                # Get pronouns
                cursor.execute(
                    "SELECT subjective, objective FROM cf_pronouns WHERE cfid = ?", (cfid,)
                )
                pronoun_data = cursor.fetchone()
                if pronoun_data:
                    profile["pronouns"]["subject_pron"] = pronoun_data[0]
                    profile["pronouns"]["objective_pron"] = pronoun_data[1]

                # Get profile notes
                cursor.execute(
                    "SELECT note_id, note, add_date, author FROM cf_profile_notes WHERE cfid = ?",
                    (cfid,),
                )
                notes_data = cursor.fetchall()
                for row in notes_data:
                    if not row or len(row) != 4:
                        continue

                    note_id, note, add_date, author = int(row), str(row[1]), row[2], str(row[3])
                    # noinspection PyTypeChecker
                    profile["profile_notes"][note_id] = {
                        "note": note,
                        "add_date": add_date,
                        "author": author,
                    }

                all_profiles.append(profile)

            return all_profiles

        finally:
            conn.close()

# noinspection PyUnusedLocal
@router.get("/files", response_class=HTMLResponse)
async def show_reg(request: Request, token: str = Depends(require_valid_token)):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/files/get/{cfid}")
async def get_file(request: Request, cfid: int, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} Has fetched the folder for cfid {cfid} under account {authbook.token_owner(token)}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "profile": profile,
        }
    )

@router.post("/api/files/modify", response_class=JSONResponse)
async def modify_file(data: ModifyFileData, token: str = Depends(require_valid_token)):
    logbook.info(f"Request from account {authbook.token_owner(token)} to modify cfid {data.cfid}: field '{data.field}' with value '{data.value}'")

    try:
        if data.field == "age":
            centralfiles.modify(data.cfid).age(int(data.value))
            success = True
        elif data.field == "pronouns":
            centralfiles.modify(data.cfid).pronouns(
                subjective=data.value.split("/")[0],
                objective=data.value.split("/")[1],
            )
            success = True
        elif data.field == "name":
            centralfiles.modify(data.cfid).name(data.value)
            success = True
        else:
            success = False

        if success:
            return JSONResponse(content={"success": True}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "error": "Update failed"}, status_code=400)

    except Exception as err:
        logbook.error(f"Error updating cfid {data.cfid}: {err}", exception=err)
        return JSONResponse(content={"success": False, "error": "Internal server error"}, status_code=500)

@router.post("/api/files/note/modify", response_class=JSONResponse)
async def modify_note(request: Request, data: NoteData, token: str = Depends(require_valid_token)):
    logbook.info(f"Request from IP {request.client.host} under account {authbook.token_owner(token)} to modify note ID {data.note_id} to \"{data.note}\"")
    success = centralfiles.notes(data.note_id).modify(data.note)
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Update failed"}, status_code=400)

@router.post("/api/files/note/delete", response_class=JSONResponse)
async def delete_note(request: Request, data: NoteDeleteData, token: str = Depends(require_valid_token)):
    logbook.info(f"Request from IP {request.client.host} to DELETE note ID {data.note_id} by account {authbook.token_owner(token)}")
    success = centralfiles.notes(data.note_id).delete()
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Deletion failed"}, status_code=400)

@router.post("/api/files/note/create", response_class=JSONResponse)
async def create_note(request: Request, data: NoteCreateData, token: str = Depends(require_valid_token)):
    logbook.info(f"Request from IP {request.client.host} to CREATE a note by account {authbook.token_owner(token)}")

    author = authbook.token_owner(token)
    note_id = centralfiles.notes.create(data.cfid, data.note, author)
    success = note_id is not None

    if success:
        return JSONResponse(content={
            "success": True,
            "note_id": note_id,
            "add_date": datetime.datetime.now(datetime.UTC).strftime("%m/%d/%Y %H:%M:%S"),
            "author": author
            },
            status_code=200
        )
    else:
        return JSONResponse(content={"success": False, "error": "Create failed"}, status_code=400)

@router.get("/api/files/get_names", response_class=HTMLResponse)
async def get_names(request: Request, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} Has fetched all names under account {authbook.token_owner(token)}")
    names, cfid_list = centralfiles.get_names()
    data = {
        "names": names,
        "cfids": cfid_list
    }
    return JSONResponse(
        content=data,
        status_code=200,
    )

@router.get("/api/files/get_all_profile", response_class=HTMLResponse)
async def get_all_profiles(request: Request, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} Has fetched all names under account {authbook.token_owner(token)}")
    data = {
        "profiles": centralfiles.get_all_profiles(),
    }
    return JSONResponse(
        content=data,
        status_code=200,
    )

@router.post("/api/files/get_profile", response_class=JSONResponse)
async def get_profile(
        request: Request,
        data: NamePostData,
        token: str = Depends(require_valid_token)
):
    try:
        profile = centralfiles.get_profile(name=data.name)
        logbook.info(f"IP {request.client.host} fetched profile '{data.name}' under account {authbook.token_owner(token)}")
        return JSONResponse(content=profile, status_code=200)
    except centralfiles.errors.ProfileNotFound:
        return JSONResponse(content={"error": "Profile not found."}, status_code=404)
    except centralfiles.errors.TooManyProfiles:
        return JSONResponse(content={"error": "Multiple profiles with that name."}, status_code=400)

@router.post("/api/files/create", response_class=JSONResponse)
async def create_name(data: NamePostData, token: str = Depends(require_valid_token)):
    logbook.info(f"Request from account {authbook.token_owner(token)} to CREATE name '{data.name}'")
    cfid = centralfiles.add_name(data.name)
    if cfid is not None:
        return JSONResponse(content={"success": True, "cfid": cfid}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Creation failed"}, status_code=400)

@router.post("/api/files/delete", response_class=JSONResponse)
async def delete_name(data: DeleteNameData, token: str = Depends(require_valid_token)):
    logbook.info(f"Request from account {authbook.token_owner(token)} to DELETE name '{data.name}'")
    success = centralfiles.delete_name(data.name)
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Deletion failed"}, status_code=400)