from modules.dianetics.routes import update_mind_class_estimation
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.authperms import set_permission
from library.auth import require_prechecks
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

    class dianetics:
        class tonescale:
            def __init__(self, cfid):
                self.cfid = int(cfid)

            def set_level(self, new_level):
                if new_level > 4.0 or new_level < 0.0:
                    raise ValueError("Invalid level")

                with sqlite3.connect(DB_PATH) as conn:
                    try:
                        cur = conn.cursor()
                        cur.execute(
                            """
                            INSERT INTO cf_tonescale_records (cfid, est_tone_level) VALUES (?, ?)
                            ON CONFLICT(cfid) DO UPDATE SET est_tone_level=excluded.est_tone_level
                            """,
                            (self.cfid, float(new_level))
                        )
                        conn.commit()
                        return True
                    except sqlite3.OperationalError as err:
                        logbook.error(f"Error setting tone level for cfid {self.cfid}: {err}", exception=err)
                        conn.rollback()
                        return False

        class modify:
            def __init__(self, cfid):
                self.cfid = int(cfid)

            def add_action(self, action:str):
                datenow = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with sqlite3.connect(DB_PATH) as conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO cf_dn_action_records (cfid, action, date) VALUES (?, ?, ?)
                            """,
                            (self.cfid, action, datenow)
                        )
                        conn.commit()
                        return True
                    except sqlite3.OperationalError as err:
                        logbook.error(f"Error adding action to cfid {self.cfid}: {err}", exception=err)
                        conn.rollback()
                        return False

            def is_sonic_off(self, new_value:bool):
                with sqlite3.connect(DB_PATH) as conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO cf_dn_shutoffs (cfid, sonic_shutoff) VALUES (?, ?)
                            ON CONFLICT(cfid) DO UPDATE SET sonic_shutoff=excluded.sonic_shutoff
                            """,
                            (self.cfid, new_value)
                        )
                        conn.commit()
                        return True
                    except sqlite3.OperationalError as err:
                        logbook.error(f"Error updating cfid {self.cfid} on is_sonic_off: {err}", exception=err)
                        conn.rollback()
                        return False

            def is_visio_off(self, new_value:bool):
                with sqlite3.connect(DB_PATH) as conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO cf_dn_shutoffs (cfid, visio_shutoff) VALUES (?, ?)
                            ON CONFLICT(cfid) DO UPDATE SET visio_shutoff=excluded.visio_shutoff
                            """,
                            (self.cfid, new_value)
                        )
                        conn.commit()
                        return True
                    except sqlite3.OperationalError as err:
                        logbook.error(f"Error updating cfid {self.cfid} on is_visio_off: {err}", exception=err)
                        conn.rollback()
                        return False

            def is_fabricator_case(self, new_value:bool):
                with sqlite3.connect(DB_PATH) as conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO cf_dn_fabricator_case (cfid, is_fabricator_case) VALUES (?, ?)
                            ON CONFLICT(cfid) DO UPDATE SET is_fabricator_case=excluded.is_fabricator_case
                            """,
                            (self.cfid, new_value)
                        )
                        conn.commit()
                        return True
                    except sqlite3.OperationalError as err:
                        logbook.error(f"Error updating cfid {self.cfid} on is_fabricator_case: {err}", exception=err)
                        conn.rollback()
                        return False

            def is_stuck_case(self, new_value:bool):
                with sqlite3.connect(DB_PATH) as conn:
                    try:
                        cur = conn.cursor()
                        cur.execute(
                            """
                            INSERT INTO cf_dn_stuck_case (cfid, is_stuck_case) VALUES (?, ?)
                            ON CONFLICT(cfid) DO UPDATE SET is_stuck_case=excluded.is_stuck_case
                            """,
                            (self.cfid, new_value)
                        )
                        conn.commit()
                        return True
                    except sqlite3.OperationalError as err:
                        logbook.error(f"Error updating cfid {self.cfid} on is_stuck_case: {err}", exception=err)
                        conn.rollback()
                        return False

            def stuck_age(self, new_value:int):
                with sqlite3.connect(DB_PATH) as conn:
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            """
                            INSERT INTO cf_dn_stuck_case (cfid, stuck_age) VALUES (?, ?)
                            ON CONFLICT(cfid) DO UPDATE SET stuck_age=excluded.stuck_age
                            """,
                            (self.cfid, new_value)
                        )
                        conn.commit()
                        return True
                    except sqlite3.OperationalError as err:
                        logbook.error(f"Error updating cfid {self.cfid} on stuck_age: {err}", exception=err)
                        conn.rollback()
                        return False

            def is_control_case(self, new_value:bool):
                with sqlite3.connect(DB_PATH) as conn:
                    try:
                        cur = conn.cursor()
                        cur.execute(
                            """
                            INSERT INTO cf_dn_control_case (cfid, is_control_case) VALUES (?, ?)
                            ON CONFLICT(cfid) DO UPDATE SET is_control_case=excluded.is_control_case
                            """,
                            (self.cfid, new_value)
                        )
                        conn.commit()
                        return True
                    except sqlite3.OperationalError as err:
                        logbook.error(f"Error updating cfid {self.cfid} on is_control_case: {err}", exception=err)
                        conn.rollback()
                        return False

        @staticmethod
        def list_actions(cfid):
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        """
                        SELECT action_id, action, date FROM cf_dn_action_records WHERE cfid = ? ORDER BY date DESC
                        """,
                        (cfid,)
                    )
                    data = cursor.fetchall()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting actions for cfid {cfid}: {err}", exception=err)
                    return []

            parsed_data = []
            for item in data:
                parsed_data.append({
                    "action_id": item[0],
                    "action": item[1],
                    "date": item[2]
                })
            return parsed_data

        @staticmethod
        def get_profile(cfid):
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "SELECT is_dn_pc FROM cf_is_dianetics_pc WHERE cfid = ?",
                        (cfid,)
                    )
                    is_dn_pc = bool(cursor.fetchone()[0])
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting is_dn_pc for cfid {cfid}: {err}", exception=err)
                    conn.rollback()
                    is_dn_pc = False
                except TypeError:
                    cursor.execute(
                        """
                        INSERT INTO cf_is_dianetics_pc (cfid, is_dn_pc) VALUES (?, ?)
                        """,
                        (cfid, False)
                    )
                    conn.commit()
                    is_dn_pc = False

                try:
                    cursor.execute(
                        """
                        SELECT is_stuck_case, stuck_age FROM cf_dn_stuck_case WHERE cfid = ?
                        """,
                        (cfid,)
                    )
                    is_stuck_case, stuck_age = cursor.fetchone()
                    is_stuck_case = bool(is_stuck_case)
                    stuck_age = int(stuck_age)
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting is_stuck_case for cfid {cfid}: {err}", exception=err)
                    conn.rollback()
                    is_stuck_case = False
                    stuck_age = -1
                except TypeError:
                    cursor.execute(
                        """
                        INSERT INTO cf_dn_stuck_case (cfid, is_stuck_case, stuck_age) VALUES (?, ?, ?)
                        """,
                        (cfid, False, -1)
                    )
                    conn.commit()
                    is_stuck_case = False
                    stuck_age = -1

                try:
                    cursor.execute(
                        """
                        SELECT is_control_case FROM cf_dn_control_case WHERE cfid = ?
                        """,
                        (cfid,)
                    )
                    is_control_case = bool(cursor.fetchone()[0])
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting is_control_case for cfid {cfid}: {err}", exception=err)
                    conn.rollback()
                    is_control_case = False
                except TypeError:
                    cursor.execute(
                        """
                        INSERT INTO cf_dn_control_case (cfid, is_control_case) VALUES (?, ?)
                        """,
                        (cfid, False)
                    )
                    conn.commit()
                    is_control_case = False

                try:
                    cursor.execute(
                        """
                        SELECT sonic_shutoff, visio_shutoff FROM cf_dn_shutoffs WHERE cfid = ?
                        """,
                        (cfid,)
                    )
                    is_sonic_shutoff, is_visio_shutoff = cursor.fetchone()
                    is_sonic_shutoff, is_visio_shutoff = bool(is_sonic_shutoff), bool(is_visio_shutoff)
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting is_sonic_shutoff or is_visio_shutoff for cfid {cfid}: {err}", exception=err)
                    conn.rollback()
                    is_sonic_shutoff, is_visio_shutoff = False, False
                except TypeError:
                    cursor.execute(
                        """
                        INSERT INTO cf_dn_shutoffs (cfid, sonic_shutoff, visio_shutoff) VALUES (?, ?, ?)
                        """,
                        (cfid, False, False)
                    )
                    conn.commit()
                    is_sonic_shutoff, is_visio_shutoff = False, False

                try:
                    cursor.execute(
                        """
                        SELECT is_fabricator_case FROM cf_dn_fabricator_case WHERE cfid = ?
                        """,
                        (cfid,)
                    )
                    conn.commit()
                    is_fabricator_case = bool(cursor.fetchone()[0])
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting is_fabricator_case for cfid {cfid}: {err}", exception=err)
                    conn.rollback()
                    is_fabricator_case = False
                except TypeError:
                    cursor.execute(
                        """
                        INSERT INTO cf_dn_fabricator_case (cfid, is_fabricator_case) VALUES (?, ?)
                        """,
                        (cfid, False)
                    )
                    conn.commit()
                    is_fabricator_case = False

                try:
                    # Gets the latest action on the PC.
                    cursor.execute(
                        """
                        SELECT action FROM cf_dn_action_records WHERE cfid = ? ORDER BY date DESC LIMIT 1
                        """,
                        (cfid,)
                    )
                    last_action = cursor.fetchone()[0]
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting last_action for cfid {cfid}: {err}", exception=err)
                    conn.rollback()
                    last_action = "Last Action Not Found"
                except TypeError:
                    last_action = "No actions performed."

                try:
                    cursor.execute(
                        """
                        SELECT est_tone_level FROM cf_tonescale_records WHERE cfid = ?
                        """,
                        (cfid,)
                    )
                    tone_level = cursor.fetchone()[0]
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting tone_level for cfid {cfid}: {err}", exception=err)
                    conn.rollback()
                    tone_level = -1
                except TypeError:
                    # Do not insert data for this one. It must be determined, not assumed. Just keep returning -1
                    tone_level = -1

                try:
                    cursor.execute(
                        """
                        SELECT actual_class, apparent_class FROM cf_pc_mind_class WHERE cfid = ?
                        """,
                        (cfid,)
                    )
                    actual_class, apparent_class = cursor.fetchone()
                    actual_class, apparent_class = int(actual_class), int(apparent_class)
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting actual_class and apparent_class for cfid {cfid}: {err}", exception=err)
                    conn.rollback()
                    actual_class, apparent_class = 0, 0
                except TypeError:
                    update_mind_class_estimation(cfid)
                    actual_class, apparent_class = 0, 0

            mind_class_map = {
                0: "Undetermined",
                1: "Class A",
                2: "Class B",
                3: "Class C",
            }

            return {
                "is_dn_pc": is_dn_pc,
                "is_stuck_case": is_stuck_case,
                "stuck_age": stuck_age,
                "is_control_case": is_control_case,
                "is_sonic_shutoff": is_sonic_shutoff,
                "is_visio_shutoff": is_visio_shutoff,
                "is_fabricator_case": is_fabricator_case,
                "tone_level": tone_level,
                "last_action": last_action,
                "mind_class_actual": mind_class_map[actual_class],
                "mind_class_apparent": mind_class_map[apparent_class],
            }

    @staticmethod
    def dupe_check(name:str):
        """
        Returns if there is someone with the same data in the database.
        """
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT cfid FROM cf_names WHERE name = ?",
                (name,)
            )
            data = cursor.fetchall()

            cfid_list = [item[0] for item in data]
            return {
                "exists": len(cfid_list) != 0,
                "cfids": cfid_list
            }
        except sqlite3.OperationalError as err:
            logbook.error(f"Error checking for duplicates: {err}")
            return {
                "exists": False,
                "error": "Database error occurred while checking for duplicates."
            }
        finally:
            conn.close()

    class modify:
        def __init__(self, cfid):
            self.cfid = int(cfid)

        def is_dn_pc(self, new_value:bool):
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO cf_is_dianetics_pc (cfid, is_dn_pc) VALUES (?, ?)
                        ON CONFLICT(cfid) DO UPDATE SET is_dn_pc=excluded.is_dn_pc
                        """,
                        (self.cfid, new_value)
                    )
                    conn.commit()
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error updating cfid {self.cfid} on is_dn_pc: {err}")
                    conn.rollback()

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
            cursor.execute(
                """
                INSERT INTO cf_is_dianetics_pc (cfid, is_dn_pc) VALUES (?, ?)
                """,
                (cfid, False)
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

            cursor.execute(
                """
                SELECT is_dn_pc FROM cf_is_dianetics_pc WHERE cfid = ?
                """,
                (cfid,),
            )
            try:
                is_dn_pc = bool(cursor.fetchone()[0])
            except (TypeError, IndexError):
                is_dn_pc = False

            profile = {
                "cfid": cfid,
                "name": name,
                "age": age,
                "pronouns": {
                    "subject_pron": subject_pron,
                    "objective_pron": objective_pron,
                },
                "profile_notes": profile_notes,
                "is_dianetics_pc": is_dn_pc
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

    @staticmethod
    def get_assosciated_invoices(cfid):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT invoice_id, date, amount, is_paid FROM invoices WHERE cfid = ?
                    """,
                    (cfid,)
                )
                rows = cur.fetchall()
                parsed_data = []
                for row in rows:
                    parsed_data.append({
                        "invoice_id": row[0],
                        "date": row[1],
                        "amount": row[2],
                        "is_paid": row[3]
                    })
                return parsed_data
            except sqlite3.OperationalError:
                conn.rollback()
                return []

    @staticmethod
    def get_assosciated_debts(cfid):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT debt_id, debtor, debtee, amount, start_date, end_date FROM debts WHERE cfid = ?
                    """,
                    (cfid,)
                )
                rows = cur.fetchall()
                parsed_data = []
                for row in rows:
                    start_date = datetime.datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S.%f").strftime("%d-%m-%Y")
                    end_date = row[5]
                    if end_date:
                        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S.%f").strftime("%d-%m-%Y")

                    parsed_data.append({
                        "debt_id": row[0],
                        "debtor": row[1],
                        "debtee": row[2],
                        "amount": row[3],
                        "start_date": start_date,
                        "end_date": end_date
                    })
                return parsed_data
            except sqlite3.OperationalError:
                conn.rollback()
                return []

# noinspection PyUnusedLocal
@router.get("/files", response_class=HTMLResponse)
@set_permission(permission="central_files")
async def show_reg(request: Request, token: str = Depends(require_prechecks)):
    return templates.TemplateResponse(request, "index.html")

@router.get("/files/dupecheck/{name}", response_class=HTMLResponse)
@set_permission(permission="central_files")
async def dupe_check(request: Request, name: str, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host}, User {authbook.token_owner(token)} Has checked for duplicates for cfid {name}")
    result = centralfiles.dupe_check(str(name))
    if result["exists"]:
        return JSONResponse(content={"exists": True, "cfids": result["cfids"]}, status_code=200)
    else:
        if result.get("error", None) is None:
            return JSONResponse(content={"exists": False}, status_code=404)
        else:
            return JSONResponse(content={"exists": -1, "error": result["error"]}, status_code=500)

@router.get("/files/get/{cfid}")
@set_permission(permission="central_files")
async def get_file(request: Request, cfid: int, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} Has fetched the folder for cfid {cfid} under account {authbook.token_owner(token)}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    assosciated_invoices = centralfiles.get_assosciated_invoices(cfid)
    assosciated_debts = centralfiles.get_assosciated_debts(cfid)
    dianetics_profile = centralfiles.dianetics.get_profile(cfid=cfid)

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "profile": profile,
            "invoices": assosciated_invoices,
            "debts": assosciated_debts,
            "dianetics": dianetics_profile
        }
    )

@router.post("/api/files/modify", response_class=JSONResponse)
@set_permission(permission="central_files")
async def modify_file(data: ModifyFileData, token: str = Depends(require_prechecks)):
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
        elif data.field == "is_dianetics":
            centralfiles.modify(data.cfid).is_dn_pc(bool(data.value))
            success = True
        elif data.field == "last_action":
            centralfiles.dianetics.modify(data.cfid).add_action(data.value)
            success = True
        elif data.field == "sonic_shutoff":
            centralfiles.dianetics.modify(data.cfid).is_sonic_off(bool(data.value))
            success = True
        elif data.field == "visio_shutoff":
            centralfiles.dianetics.modify(data.cfid).is_visio_off(bool(data.value))
            success = True
        elif data.field == "stuck_case":
            centralfiles.dianetics.modify(data.cfid).is_stuck_case(bool(data.value))
            success = True
        elif data.field == "stuck_age":
            centralfiles.dianetics.modify(data.cfid).stuck_age(int(data.value))
            success = True
        elif data.field == "control_case":
            centralfiles.dianetics.modify(data.cfid).is_control_case(bool(data.value))
            success = True
        elif data.field == "fabricator_case":
            centralfiles.dianetics.modify(data.cfid).is_fabricator_case(bool(data.value))
            success = True
        elif data.field == "tone_level":
            centralfiles.dianetics.tonescale(data.cfid).set_level(float(data.value))
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
@set_permission(permission="central_files")
async def modify_note(request: Request, data: NoteData, token: str = Depends(require_prechecks)):
    logbook.info(f"Request from IP {request.client.host} under account {authbook.token_owner(token)} to modify note ID {data.note_id} to \"{data.note}\"")
    success = centralfiles.notes(data.note_id).modify(data.note)
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Update failed"}, status_code=400)

@router.post("/api/files/note/delete", response_class=JSONResponse)
@set_permission(permission="central_files")
async def delete_note(request: Request, data: NoteDeleteData, token: str = Depends(require_prechecks)):
    logbook.info(f"Request from IP {request.client.host} to DELETE note ID {data.note_id} by account {authbook.token_owner(token)}")
    success = centralfiles.notes(data.note_id).delete()
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Deletion failed"}, status_code=400)

@router.post("/api/files/note/create", response_class=JSONResponse)
@set_permission(permission="central_files")
async def create_note(request: Request, data: NoteCreateData, token: str = Depends(require_prechecks)):
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
@set_permission(permission="central_files")
async def get_names(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} Has fetched all names under account {authbook.token_owner(token)}")
    names, cfid_list = centralfiles.get_names() # type: ignore
    data = {
        "names": names,
        "cfids": cfid_list
    }
    return JSONResponse(
        content=data,
        status_code=200,
    )

@router.get("/api/files/get_all_profile", response_class=HTMLResponse)
@set_permission(permission="central_files")
async def get_all_profiles(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} Has fetched all names under account {authbook.token_owner(token)}")
    data = {
        "profiles": centralfiles.get_all_profiles(),
    }
    return JSONResponse(
        content=data,
        status_code=200,
    )

@router.post("/api/files/get_profile", response_class=JSONResponse)
@set_permission(permission="central_files")
async def get_profile(request: Request, data: NamePostData, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} fetched profile '{data.name}' under account {authbook.token_owner(token)}")
    try:
        profile = centralfiles.get_profile(name=data.name)
        return JSONResponse(content=profile, status_code=200)
    except centralfiles.errors.ProfileNotFound:
        return JSONResponse(content={"error": "Profile not found."}, status_code=404)
    except centralfiles.errors.TooManyProfiles:
        return JSONResponse(content={"error": "Multiple profiles with that name."}, status_code=400)

@router.post("/api/files/create", response_class=JSONResponse)
@set_permission(permission="central_files")
async def create_name(request: Request, data: NamePostData, token: str = Depends(require_prechecks)):
    logbook.info(f"Request from IP {request.client.host}; Request from account {authbook.token_owner(token)} to CREATE name '{data.name}'")
    cfid = centralfiles.add_name(data.name)
    if cfid is not None:
        return JSONResponse(content={"success": True, "cfid": cfid}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Creation failed"}, status_code=400)

@router.post("/api/files/delete", response_class=JSONResponse)
@set_permission(permission="central_files")
async def delete_name(request: Request, data: DeleteNameData, token: str = Depends(require_prechecks)):
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to DELETE name '{data.name}'")
    success = centralfiles.delete_name(data.name)
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Deletion failed"}, status_code=400)

class SubmitActionData(BaseModel):
    cfid: int
    action: str

@router.post("/api/files/submit_action", response_class=JSONResponse)
@set_permission(permission="central_files")
async def submit_action(request: Request, data: SubmitActionData, token: str = Depends(require_prechecks)):
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to SUBMIT action '{data.action}' for cfid {data.cfid}")
    success = centralfiles.dianetics.modify(data.cfid).add_action(data.action)
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Action submission failed"}, status_code=400)

@router.get("/api/files/get_actions/{cfid}", response_class=JSONResponse)
@set_permission(permission="central_files")
async def submit_action(request: Request, cfid, token: str = Depends(require_prechecks)):
    logbook.info(f"Request from IP {request.client.host}; Request from account {authbook.token_owner(token)} to get all actions for cfid {cfid}")
    actions = centralfiles.dianetics.list_actions(cfid)
    return JSONResponse(content=actions, status_code=200)
