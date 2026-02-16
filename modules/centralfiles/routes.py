from fastapi.responses import JSONResponse, HTMLResponse, Response
from library.authperms import set_permission, AuthPerms
from fastapi.templating import Jinja2Templates
from library.logbook import LogBookHandler
from library.auth import route_prechecks
from fastapi import APIRouter, Request
from library.database import DB_PATH
from library.auth import authbook
from typing import Dict, Optional
from collections import Counter
from pydantic import BaseModel
import asyncio
import datetime
import sqlite3
import base64
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
    cfid: int

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

            def set_theta_count(self, count:int):
                with sqlite3.connect(DB_PATH) as conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO cf_pc_theta_endowments (cfid, endowment) VALUES (?, ?)
                            ON CONFLICT(cfid) DO UPDATE SET endowment=excluded.endowment
                            """,
                            (self.cfid, count)
                        )
                        conn.commit()
                        return True
                    except sqlite3.OperationalError as err:
                        logbook.error(f"Error setting CFID {self.cfid}'s theta count to {count}: {err}", exception=err)
                        conn.rollback()
                        return False

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

                try:
                    cursor.execute(
                        """
                        SELECT endowment FROM cf_pc_theta_endowments WHERE cfid = ?
                        """,
                        (cfid,)
                    )
                    theta_endowment = cursor.fetchone()[0]
                    theta_endowment = int(theta_endowment)
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting the theta endowment for cfid {cfid}: {err}", exception=err)
                    conn.rollback()
                    theta_endowment = 0
                except TypeError:
                    theta_endowment = 0

                try:
                    cursor.execute(
                        """
                        SELECT is_handleable FROM cf_pc_can_handle_life WHERE cfid = ?
                        """,
                        (cfid,)
                    )
                    can_handle_life = cursor.fetchone()[0]
                    can_handle_life = bool(can_handle_life)
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting if the PC can handle life or not for cfid {cfid}: {err}", exception=err)
                    conn.rollback()
                    can_handle_life = True
                except TypeError:
                    can_handle_life = True

                try:
                    cursor.execute(
                        """
                        SELECT on_chem_assist FROM cf_chem_assist WHERE cfid = ?
                        """,
                        (cfid,)
                    )
                    on_chem_assist = cursor.fetchone()[0]
                    on_chem_assist = bool(on_chem_assist)
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error getting if the PC is on a chemical assist for cfid {cfid}: {err}", exception=err)
                    conn.rollback()
                    on_chem_assist = False
                except TypeError:
                    on_chem_assist = False

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
                "theta_endowment": theta_endowment,
                "can_handle_life": can_handle_life,
                "chem_assist": on_chem_assist
            }

    class modify:
        def __init__(self, cfid):
            self.cfid = int(cfid)

        def phone_no(self, value):
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO cf_pc_contact_details (cfid, phone_no) VALUES (?, ?)
                        ON CONFLICT(cfid) DO UPDATE SET phone_no=excluded.phone_no
                        """,
                        (self.cfid, value)
                    )
                    conn.commit()
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error updating cfid {self.cfid}'s phone number: {err}", exception=err)
                    conn.rollback()
                    return False

        def profile_type(self, value):
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO cf_name_types (cfid, nametype) VALUES (?, ?)
                        ON CONFLICT(cfid) DO UPDATE SET nametype=excluded.nametype
                        """,
                        (self.cfid, value)
                    )
                    conn.commit()
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error updating cfid {self.cfid}'s profile type: {err}", exception=err)
                    conn.rollback()
                    return False

        def email_address(self, value):
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO cf_pc_contact_details (cfid, email_addr) VALUES (?, ?)
                        ON CONFLICT(cfid) DO UPDATE SET email_addr=excluded.email_addr
                        """,
                        (self.cfid, value)
                    )
                    conn.commit()
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error updating cfid {self.cfid}'s email address: {err}", exception=err)
                    conn.rollback()
                    return False

        def home_address(self, value):
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO cf_pc_contact_details (cfid, home_addr) VALUES (?, ?)
                        ON CONFLICT(cfid) DO UPDATE SET home_addr=excluded.home_addr
                        """,
                        (self.cfid, value)
                    )
                    conn.commit()
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error updating cfid {self.cfid}'s home address: {err}", exception=err)
                    conn.rollback()
                    return False

        def chem_assist(self, value):
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO cf_chem_assist (cfid, on_chem_assist) VALUES (?, ?)
                        ON CONFLICT(cfid) DO UPDATE SET on_chem_assist=excluded.on_chem_assist
                        """,
                        (self.cfid, value)
                    )
                    conn.commit()
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error updating cfid {self.cfid} on whether or not they're on a chemical assist: {err}", exception=err)
                    conn.rollback()
                    return False

        def can_handle_life(self, value:bool):
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO cf_pc_can_handle_life (cfid, is_handleable) VALUES (?, ?)
                        ON CONFLICT(cfid) DO UPDATE SET is_handleable=excluded.is_handleable
                        """,
                        (self.cfid, value)
                    )
                    conn.commit()
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error updating cfid {self.cfid} on whether or not they can usually handle life: {err}", exception=err)
                    conn.rollback()
                    return False

        def date_of_birth(self, date_of_birth):
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO cf_dates_of_birth (cfid, date_of_birth) VALUES (?, ?)
                        ON CONFLICT(cfid) DO UPDATE SET date_of_birth=excluded.date_of_birth
                        """,
                        (self.cfid, date_of_birth)
                    )
                    conn.commit()
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error updating cfid {self.cfid} on what their Date of Birth is: {err}", exception=err)
                    conn.rollback()
                    return False

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
                    return False

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

        def profile_image(self, image_bytes:bytes):
            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO cf_profile_images (cfid, image) VALUES (?, ?)
                    ON CONFLICT(cfid) DO UPDATE SET image=excluded.image
                    """,
                    (self.cfid, image_bytes)
                )
                conn.commit()
                return True
            except sqlite3.OperationalError as err:
                logbook.error(f"Error setting profile image for cfid {self.cfid}: {err}", exception=err)
                conn.rollback()
                return False
            finally:
                conn.close()

        def occupation(self, occupation):
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO cf_occupations (cfid, occupation) VALUES (?, ?)
                        ON CONFLICT(cfid) DO UPDATE SET occupation=excluded.occupation
                        """,
                        (self.cfid, occupation)
                    )
                    conn.commit()
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error setting occupation for cfid {self.cfid}: {err}", exception=err)
                    conn.rollback()
                    return False

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

    class agreements:
        @staticmethod
        def delete(cfid:int, agreement_id:int):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        DELETE FROM cf_agreements WHERE cfid = ? AND agreement_id = ?;
                        """,
                        (cfid, agreement_id,)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error while trying to delete the agreement with ID \"{agreement_id}\" from the Database for CFID {cfid}: {err}", exception=err)
                    return False

        @staticmethod
        def get_agreements(cfid):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        SELECT agreement_id, agreement, date_of_agreement, fulfilled FROM cf_agreements WHERE cfid = ?
                        """,
                        (cfid,)
                    )
                    data = cur.fetchall()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error while trying to fetch agreements from the Database for CFID {cfid}: {err}", exception=err)
                    return False

            parsed_data = []
            for row in data:
                date_agreed = datetime.datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
                parsed_data.append({
                    "agreement_id": row[0],
                    "agreement": row[1],
                    "date": date_agreed,
                    "fulfilled": row[3]
                })
            return parsed_data

        @staticmethod
        def set_fulfilled_status(value:bool, agreement_id, cfid):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        UPDATE cf_agreements 
                        SET fulfilled = ? 
                        WHERE agreement_id = ? AND cfid = ?
                        """,
                        (value, agreement_id, cfid)
                    )
                    conn.commit()
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error while trying to fetch agreements from the Database for CFID {cfid}: {err}", exception=err)
                    return False

        def add_agreement(cfid:int, agreement:str, date_agreed:datetime.datetime):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        INSERT INTO cf_agreements (cfid, agreement, date_of_agreement, fulfilled)
                        VALUES (?, ?, ?, ?)
                        """,
                        (cfid, agreement, date_agreed, False)
                    )
                    conn.commit()
                    success = True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error while trying to fetch agreements from the Database for CFID {cfid}: {err}", exception=err)
                    success = False
            return success

    @staticmethod
    def get_occupation(cfid:int):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT occupation FROM cf_occupations WHERE cfid = ?",
                    (cfid,)
                )
                data = cursor.fetchone()
                if data:
                    return data[0]
                else:
                    return "Unemployed"
            except sqlite3.OperationalError as err:
                logbook.error(f"Error getting occupation for cfid {cfid}: {err}", exception=err)
                return "Unemployed"

    @staticmethod
    def get_profile_image(cfid):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT image FROM cf_profile_images WHERE cfid = ?",
                    (cfid,)
                )
                data = cursor.fetchone()
                if data:
                    return data[0]
                else:
                    return None
            except sqlite3.OperationalError as err:
                logbook.error(f"Error getting profile image for cfid {cfid}: {err}", exception=err)
                return None

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

    @staticmethod
    def get_profile_is_staff(cfid):
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT username from cf_staff_usernames WHERE cfid = ?
                """,
                (cfid,),
            )
            data = cursor.fetchone()
            if data:
                is_staff = bool(data[0])
            else:
                is_staff = False
            return is_staff
        except sqlite3.OperationalError:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def add_name(name, staff_username=None):
        """
        Docstring for add_name
        
        :param name: The full name for the person being added
        :param staff_username: If the user is staff, enter their username and we'll assosciate the username with the person.
        """
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
            if staff_username is not None:
                cursor.execute(
                    "INSERT INTO cf_staff_usernames (cfid, username) VALUES (?, ?)",
                    (cfid, staff_username)
                )
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
            cursor.execute(
                """
                INSERT INTO cf_occupations (cfid, occupation) VALUES (?, ?)
                """,
                (cfid, "Unemployed")
            )

            conn.commit()
            return cfid
        except sqlite3.OperationalError:
            conn.rollback()
        finally:
            conn.close()

    @staticmethod
    def delete_name(cfid):
        is_staff = centralfiles.get_profile_is_staff(cfid)
        if is_staff:
            return -1

        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM cf_names WHERE cfid = ?",
                (cfid,),
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

        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                if cfid is None:
                    cursor.execute(
                        "SELECT cfid, name FROM cf_names WHERE name = ?",
                        (name,),
                    )
                    data = cursor.fetchall()
                    if len(data) == 0:
                        raise centralfiles.errors.ProfileNotFound()
                    elif len(data) != 1:
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
                    try:
                        cfid = data[0]
                        name = data[1]
                    except TypeError:
                        return False

                cfid = int(cfid)
                name = str(name)

                # Gets the age, pronouns, and all case notes.
                cursor.execute(
                    """
                    SELECT age from cf_ages WHERE cfid = ?
                    """,
                    (cfid,),
                )
                stored_age = cursor.fetchone()[0]

                # Gets the profile type of the individual
                cursor.execute(
                    """
                    SELECT nametype from cf_name_types WHERE cfid = ?
                    """,
                    (cfid,),
                )
                profile_type = cursor.fetchone()
                if not profile_type:
                    profile_type = "Unspecified"
                else:
                    profile_type = profile_type[0]

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
                    SELECT note_id, note, add_date, author FROM cf_profile_notes WHERE cfid = ? ORDER BY add_date DESC
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

                cursor.execute(
                    """
                    SELECT occupation FROM cf_occupations WHERE cfid = ?
                    """,
                    (cfid,),
                )
                try:
                    occupation = str(cursor.fetchone()[0])
                except (TypeError, IndexError):
                    occupation = "Unemployed"

                cursor.execute(
                    """
                    SELECT date_of_birth FROM cf_dates_of_birth WHERE cfid = ?
                    """,
                    (cfid,)
                )
                try:
                    data = cursor.fetchone()
                    date_of_birth = data[0]
                except (TypeError, IndexError):
                    date_of_birth = None

                # Parse and store original datetime for age calculation
                dob_for_age = None
                if type(date_of_birth) is str:
                    dob_for_age = datetime.datetime.strptime(date_of_birth, "%Y-%m-%d %H:%M:%S")
                    date_of_birth = dob_for_age.strftime("%d/%m/%Y")
                elif type(date_of_birth) == datetime.datetime:
                    dob_for_age = date_of_birth
                    date_of_birth = date_of_birth.strftime("%d/%m/%Y")

                # Calculate age if we have a valid date of birth
                # We calculate this each time so the age is ALWAYS accurate.
                if dob_for_age:
                    today = datetime.datetime.now()
                    calced_age = today.year - dob_for_age.year - ((today.month, today.day) < (dob_for_age.month, dob_for_age.day))
                    # Update the age in the database
                    if calced_age > stored_age:
                        cursor.execute(
                            """
                            INSERT INTO cf_ages (cfid, age) VALUES (?, ?)
                            ON CONFLICT(cfid) DO UPDATE SET age=excluded.age
                            """,
                            (cfid, calced_age)
                        )
                        stored_age = calced_age
                    conn.commit()

                cursor.execute(
                    """
                    SELECT phone_no, email_addr, home_addr FROM cf_pc_contact_details WHERE cfid = ?
                    """,
                    (cfid,),
                )
                try:
                    data = cursor.fetchone()
                    phone_no, email_addr, home_addr = data
                except (TypeError, IndexError):
                    phone_no, email_addr, home_addr = None, None, None
            except TypeError as err:
                logbook.error("Something went wrong fetching the data for a profile!", exception=err)
                raise err

        profile = {
            "cfid": cfid,
            "name": name,
            "age": stored_age,
            "occupation": occupation,
            "pronouns": {
                "subject_pron": subject_pron,
                "objective_pron": objective_pron,
            },
            "profile_notes": profile_notes,
            "is_dianetics_pc": is_dn_pc,
            "date_of_birth": date_of_birth,
            "phone_no": phone_no,
            "email_addr": email_addr,
            "home_addr": home_addr,
            "type": profile_type,
            "is_staff": authbook.check_exists(cfid=cfid)
        }

        return profile

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
async def show_reg(request: Request):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host}, User {authbook.token_owner(token)} has accessed the C/F Page.")
    return templates.TemplateResponse(request, "index.html")

@router.get("/files/dupecheck/{name}", response_class=HTMLResponse)
@set_permission(permission="central_files")
async def dupe_check(request: Request, name: str):
    token:str = route_prechecks(request)
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
async def get_file(request: Request, cfid: int):
    token:str = route_prechecks(request)
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
async def modify_file(request: Request, data: ModifyFileData):
    token:str = route_prechecks(request)
    user = authbook.token_owner(token)
    logbook.info(f"Request from {request.client.host} ({user}) to modify cfid {data.cfid}: field '{data.field}' with value '{data.value}'")
    is_staff = centralfiles.get_profile_is_staff(data.cfid)

    dn_fields = [
        'is_dianetics',
        'last_action',
        'sonic_shutoff',
        'visio_shutoff',
        'stuck_case',
        'stuck_age',
        'control_case',
        'fabricator_case',
        'tone_level',
        'can_handle_life',
        'chem_assist'
    ]

    try:
        if data.field == "age":
            centralfiles.modify(data.cfid).age(int(data.value))
            success = True
        elif data.field == "dob":
            if data.value.count("-") == 0:
                return JSONResponse(content={"success": False, "error": "Invalid time format"}, status_code=400)

            datetime_obj = datetime.datetime.now().strptime(data.value.lower(), "%Y-%m-%d")
            centralfiles.modify(data.cfid).date_of_birth(
                date_of_birth=datetime_obj
            )
            success = True
        elif data.field == "occupation":
            if is_staff:
                return JSONResponse(content={"success": False, "error": "You cannot modify a staff members occupation using CF."}, status_code=400)
            centralfiles.modify(data.cfid).occupation(data.value)
            success = True
        elif data.field == "pronouns":
            if not len(data.value.split("/")) == 2:
                return JSONResponse(content={"success": False, "error": "Format for pronouns is Invalid. Enter pronouns like She/Her or They/Him"}, status_code=400)
            centralfiles.modify(data.cfid).pronouns(
                subjective=data.value.split("/")[0],
                objective=data.value.split("/")[1],
            )
            success = True
        elif data.field == "name":
            centralfiles.modify(data.cfid).name(data.value)
            success = True
        elif data.field == "phone_no":
            centralfiles.modify(data.cfid).phone_no(data.value)
            success = True
        elif data.field == "email_addr":
            centralfiles.modify(data.cfid).email_address(data.value)
            success = True
        elif data.field == "home_addr":
            centralfiles.modify(data.cfid).home_address(data.value)
            success = True
        elif data.field == "prof_type":
            centralfiles.modify(data.cfid).profile_type(data.value)
            success = True
        else:
            if data.field not in dn_fields:
                raise ValueError(f"Invalid field specified, {data.field}")

        # Permission protected fields.
        if data.field in dn_fields:
            if AuthPerms.check_allowed(user, "dianetics") is False:
                logbook.warning(f"User {user} attempted to modify Dianetics field '{data.field}' without permission.")
                return JSONResponse(content={"success": False, "error": "Insufficient permissions to modify Dianetics fields."}, status_code=403)

            if data.field == "is_dianetics":
                centralfiles.modify(data.cfid).is_dn_pc(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "last_action":
                centralfiles.dianetics.modify(data.cfid).add_action(data.value)
                success = True
            elif data.field == "sonic_shutoff":
                centralfiles.dianetics.modify(data.cfid).is_sonic_off(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "visio_shutoff":
                centralfiles.dianetics.modify(data.cfid).is_visio_off(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "stuck_case":
                centralfiles.dianetics.modify(data.cfid).is_stuck_case(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "stuck_age":
                centralfiles.dianetics.modify(data.cfid).stuck_age(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "control_case":
                centralfiles.dianetics.modify(data.cfid).is_control_case(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "fabricator_case":
                centralfiles.dianetics.modify(data.cfid).is_fabricator_case(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "tone_level":
                centralfiles.dianetics.tonescale(data.cfid).set_level(float(data.value))
                success = True
            elif data.field == "can_handle_life":
                centralfiles.modify(data.cfid).can_handle_life(data.value)
                success = True
            elif data.field == "chem_assist":
                centralfiles.modify(data.cfid).chem_assist(data.value)
                success = True
            else:
                success = False

            if data.field in ['can_handle_life', 'visio_shutoff', 'sonic_shutoff']:
                # Update mind class estimation if these fields are changed
                update_mind_class_estimation(str(data.cfid))

        if success:
            return JSONResponse(content={"success": True}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "error": "Update failed"}, status_code=400)
    except Exception as err:
        logbook.error(f"Error updating cfid {data.cfid}: {err}", exception=err)
        return JSONResponse(content={"success": False, "error": "Internal server error"}, status_code=500)

@router.post("/api/files/note/modify", response_class=JSONResponse)
@set_permission(permission="central_files")
async def modify_note(request: Request, data: NoteData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host} under account {authbook.token_owner(token)} to modify note ID {data.note_id} to \"{data.note}\"")
    success = centralfiles.notes(data.note_id).modify(data.note)
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Update failed"}, status_code=400)

@router.post("/api/files/note/delete", response_class=JSONResponse)
@set_permission(permission="central_files")
async def delete_note(request: Request, data: NoteDeleteData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host} to DELETE note ID {data.note_id} by account {authbook.token_owner(token)}")
    success = centralfiles.notes(data.note_id).delete()
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Deletion failed"}, status_code=400)

@router.post("/api/files/note/create", response_class=JSONResponse)
@set_permission(permission="central_files")
async def create_note(request: Request, data: NoteCreateData):
    token:str = route_prechecks(request)
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
async def get_names(request: Request):
    token:str = route_prechecks(request)
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
@set_permission(permission="central_files")
async def get_all_profiles(request: Request):
    token:str = route_prechecks(request)
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
async def get_profile(request: Request, data: NamePostData):
    token:str = route_prechecks(request)
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
async def create_name(request: Request, data: NamePostData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; Request from account {authbook.token_owner(token)} to CREATE name '{data.name}'")
    cfid = centralfiles.add_name(data.name)
    if cfid is not None:
        return JSONResponse(content={"success": True, "cfid": cfid}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Creation failed"}, status_code=400)

@router.post("/api/files/delete", response_class=JSONResponse)
@set_permission(permission="central_files")
async def delete_name(request: Request, data: DeleteNameData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to DELETE CFID '{data.cfid}'")
    success = centralfiles.delete_name(data.cfid)
    if success is True:
        return JSONResponse(content={"success": True}, status_code=200)
    elif success == -1:  # Staff account
        return JSONResponse(
            content={
                "success": False,
                "error": "This is a staff account, and can only be deleted through the staff management portal."
            },
            status_code=401
        )
    else:
        return JSONResponse(content={"success": False, "error": "Deletion failed"}, status_code=400)

class SubmitActionData(BaseModel):
    cfid: int
    action: str

@router.post("/api/files/submit_action", response_class=JSONResponse)
@set_permission(["central_files", "dianetics"])
async def submit_action(request: Request, data: SubmitActionData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to SUBMIT action '{data.action}' for cfid {data.cfid}")
    success = centralfiles.dianetics.modify(data.cfid).add_action(data.action)
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Action submission failed"}, status_code=400)

@router.get("/api/files/get_actions/{cfid}", response_class=JSONResponse)
@set_permission(["central_files", "dianetics"])
async def submit_action(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; Request from account {authbook.token_owner(token)} to get all auditing actions for cfid {cfid}")
    actions = centralfiles.dianetics.list_actions(cfid)
    return JSONResponse(content=actions, status_code=200)

@router.get("/api/files/{cfid}/profile_icon")
@set_permission(permission="central_files")
async def get_profile_image(request: Request, cfid: int):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to get profile image for cfid {cfid}")
    image_data = centralfiles.get_profile_image(cfid)
    
    # Return the image bytes with appropriate headers
    return Response(
        content=image_data,
        media_type="image/jpeg"  # or "image/png", "image/gif" depending on your image format
    )

# Simple in-memory cache with TTL
class ProfileCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default TTL
        self.cache: Dict[int, Dict] = {}
        self.timestamps: Dict[int, float] = {}
        self.ttl = ttl_seconds
        self.lock = asyncio.Lock()
    
    async def get(self, cfid: int) -> Optional[Dict]:
        async with self.lock:
            if cfid in self.cache:
                # Check if cache entry is still valid
                if asyncio.get_event_loop().time() - self.timestamps[cfid] < self.ttl:
                    return self.cache[cfid]
                else:
                    # Remove expired entry
                    del self.cache[cfid]
                    del self.timestamps[cfid]
            return None
    
    async def set(self, cfid: int, profile: Dict):
        async with self.lock:
            self.cache[cfid] = profile
            self.timestamps[cfid] = asyncio.get_event_loop().time()
    
    async def invalidate(self, cfid: int):
        async with self.lock:
            if cfid in self.cache:
                del self.cache[cfid]
                del self.timestamps[cfid]

# Initialize cache
profile_cache = ProfileCache()

async def get_cached_profile(cfid: int) -> Optional[Dict]:
    """Get profile from cache or database with caching"""
    # Try cache first
    cached_profile = await profile_cache.get(cfid)
    if cached_profile:
        logbook.info(f"Cache hit for profile cfid {cfid}")
        return cached_profile
    
    # Cache miss, fetch from database
    profile = centralfiles.get_profile(cfid=cfid)
    if profile:
        await profile_cache.set(cfid, profile)
    
    return profile

# Helper function for common response logic
async def get_profile_field(cfid: int, field_name: str, field_display_name: str, request: Request, token: str):
    """Helper to get a specific field from profile with caching"""
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to get profile {field_display_name} for cfid {cfid}")
    
    profile = await get_cached_profile(cfid)
    if not profile:
        return HTMLResponse(content="Profile Not Found", status_code=404)
    
    field_value = profile.get(field_name)
    if field_value is None:
        return HTMLResponse(content=f"{field_display_name.capitalize()} Not Available", status_code=404)
    
    return HTMLResponse(content=field_value, status_code=200)

# Used by invoicing
@router.get("/api/files/{cfid}/name")
@set_permission(permission="central_files")
async def get_profile_name(request: Request, cfid: int):
    token:str = route_prechecks(request)
    return await get_profile_field(cfid, 'name', 'name', request, token)

# Used by invoicing
@router.get("/api/files/{cfid}/address")
@set_permission(permission="central_files")
async def get_profile_address(request: Request, cfid: int):
    token:str = route_prechecks(request)
    return await get_profile_field(cfid, 'home_addr', 'address', request, token)

@router.get("/api/files/{cfid}/email")
@set_permission(permission="central_files")
async def get_profile_email(request: Request, cfid: int):
    token:str = route_prechecks(request)
    return await get_profile_field(cfid, 'email_addr', 'email', request, token)

@router.get("/api/files/{cfid}/phone")
@set_permission(permission="central_files")
async def get_profile_phone(request: Request, cfid: int):
    token:str = route_prechecks(request)
    return await get_profile_field(cfid, 'phone_no', 'phone number', request, token)

@router.get("/api/files/{cfid}/is_staff")
@set_permission(permission="central_files")
async def get_profile_is_staff(request: Request, cfid: int):
    route_prechecks(request)
    return {
        "is_staff": centralfiles.get_profile_is_staff(cfid)
    }

class UploadProfileImageData(BaseModel):
    cfid: int
    img_bytes: bytes

@router.post("/api/files/upload_profile_picture", response_class=JSONResponse)
@set_permission(permission="central_files")
async def upload_profile_image(request: Request, data: UploadProfileImageData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to upload profile image for cfid {data.cfid}")
    
    try:
        # Decode base64 string back to bytes
        file_bytes = base64.b64decode(data.img_bytes)
        
        success = centralfiles.modify(data.cfid).profile_image(file_bytes)
        if success:
            return JSONResponse(content={"success": True}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "error": "Upload failed"}, status_code=400)

    except base64.binascii.Error as e:
        logbook.error(f"Base64 decoding error for cfid {data.cfid}: {e}")
        return JSONResponse(content={"success": False, "error": "Invalid image data format"}, status_code=400)
    except Exception as e:
        logbook.error(f"Unexpected error uploading profile image for cfid {data.cfid}: {e}")
        return JSONResponse(content={"success": False, "error": "Internal server error"}, status_code=500)

@router.get("/api/files/{cfid}/occupation")
@set_permission(permission="central_files")
async def get_occupation(request: Request, cfid: int):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to get the occupation for cfid {cfid}")
    try:
        occupation_data = centralfiles.get_occupation(cfid)
    except centralfiles.errors.ProfileNotFound:
        return JSONResponse(content={"error": "Profile not found."}, status_code=404)
    return HTMLResponse(occupation_data, status_code=200)

# A Webpage for full PC Management
@router.get("/files/get/{cfid}/auditing")
@set_permission(["central_files", "dianetics"])
async def load_pc_file(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has accessed the PC folder of {cfid}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    dianetics_profile = centralfiles.dianetics.get_profile(cfid=cfid)
    return templates.TemplateResponse(
        request,
        "pc_profile.html",
        {
            "profile": profile,
            "dianetics": dianetics_profile
        }
    )

class SetThetaData(BaseModel):
    cfid: int
    theta_count: int

@router.post("/api/files/set_theta")
@set_permission(["central_files", "dianetics"])
async def set_theta(request: Request, post_data: SetThetaData):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is setting CFID {post_data.cfid}'s Theta Count to {post_data.theta_count}")
    success = centralfiles.dianetics.modify(post_data.cfid).set_theta_count(post_data.theta_count)
    update_mind_class_estimation(str(post_data.cfid))

    return JSONResponse(
        content={"success": success},
        status_code=200 if success else 500
    )

@router.get("/files/get/{cfid}/agreements")
@set_permission(permission="central_files")
async def load_agreements_page(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has accessed the PC folder of {cfid}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    return templates.TemplateResponse(
        request,
        "agreements.html",
        {
            "profile": profile,
        }
    )

class add_agreement_data(BaseModel):
    agreement: str
    date_promised: str

@router.post("/api/files/{cfid}/agreements/add")
@set_permission(permission="central_files")
async def route_add_agreement(request: Request, data:add_agreement_data, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has added an agreement for CFID {cfid}, that agreement being \"{data.agreement}\"")
    
    try:
        data.date_promised = datetime.datetime.strptime(data.date_promised, "%Y-%m-%d")
    except ValueError as err:
        return JSONResponse(
            content={
                "error": str(err)
            },
            status_code=400
        )

    success = centralfiles.agreements.add_agreement(
        cfid=cfid,
        agreement=data.agreement,
        date_agreed=data.date_promised
    )

    return JSONResponse(
        content={
            "success": success
        },
        status_code=200
    )

@router.get('/api/files/{cfid}/agreements/get')
@set_permission(permission="central_files")
async def route_get_agreements(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is listing all agreements with CFID {cfid}.")

    agreements_list:list = centralfiles.agreements.get_agreements(cfid=cfid)

    if agreements_list is False:
        return JSONResponse(
            content={'error': "Couldn't get the list of agreements."},
            status_code=400
        )

    return JSONResponse(
        content=agreements_list,
        status_code=200
    )

class SetFulfilledData(BaseModel):
    agreement_id: int
    value: bool

@router.post('/api/files/{cfid}/agreements/set')
@set_permission(permission="central_files")
async def route_set_fulfilled_status(request: Request, data: SetFulfilledData, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is listing all agreements with CFID {cfid}.")

    success = centralfiles.agreements.set_fulfilled_status(cfid=int(cfid), agreement_id=int(data.agreement_id), value=bool(data.value))

    return HTMLResponse(
        content=str(success),
        status_code=200
    )

class DelAgreementData(BaseModel):
    agreement_id: int

@router.post('/api/files/{cfid}/agreements/delete')
@set_permission(permission="central_files")
async def route_set_fulfilled_status(request: Request, data: DelAgreementData, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is listing all agreements with CFID {cfid}.")

    success = centralfiles.agreements.delete(cfid=cfid, agreement_id=int(data.agreement_id))

    return HTMLResponse(
        content=str(success),
        status_code=200
    )
 
class AuditingLog:
    def list_all_sessions(cfid):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT session_id, date, summary, duration, status_code FROM sessions_list WHERE preclear_cfid = ?
                    """,
                    (cfid,)
                )
                data = cur.fetchall()
            except sqlite3.OperationalError as err:
                logbook.error(f"Error while fetching all session actions for CFID {cfid}", exception=err)
                return False
            
        parsed_data = []
        for row in data:
            parsed_data.append({
                "session_id": row[0],
                "date": row[1],
                "summary": str(row[2]),
                "duration": int(row[3]),
                "status_code": int(row[4]),
            })
        return parsed_data

    def new_session(date:datetime.datetime, cfid:int, auditor:str):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO sessions_list (date, summary, duration, auditor, preclear_cfid, status_code)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (date, "Enter a summary!", 0, auditor, cfid, 2)
                )
                conn.commit()
                session_id = cur.lastrowid
            except sqlite3.OperationalError as err:
                logbook.error(f"Error while fetching all session actions for CFID {cfid}", exception=err)
                return False

        return session_id

    class session:
        def __init__(self, session_id):
            self.session_id = int(session_id)
            self.data = self.get_session_details()
            if self.data is False:
                raise LookupError("Could not find session")  # Session non-existent.

        def set_status(self, value:int=1):
            # Stat 1 = Comp'd, Stat 2 = Pending, Stat 3 = Cancelled
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        UPDATE sessions_list
                        SET status_code = ? WHERE session_id = ?
                        """,
                        (value, self.session_id)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't mark session as code {value}!", exception=err)
                    return False
            return True

        def delete_action(self, action_id:int):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        DELETE FROM session_actions WHERE action_id = ?
                        """,
                        (int(action_id),)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't delete an action from the DB: {err}", exception=err)
                    return False
            return True

        def set_action_status(self, status, action_id):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        UPDATE session_actions
                        SET completed = ? WHERE action_id = ?
                        """,
                        (bool(status), int(action_id))
                    )
                    conn.commit()
                    return cur.lastrowid
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't set an action's status for the DB: {err}", exception=err)
                    return False

        def add_action(self, action_text):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        INSERT INTO session_actions (session_id, action, completed)
                        VALUES (?, ?, ?)
                        """,
                        (self.session_id, action_text, False)
                    )
                    conn.commit()
                    return cur.lastrowid
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't add an action to the DB: {err}", exception=err)
                    return False

        def delete_engram(self, engram_id):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        DELETE FROM session_engrams WHERE session_id = ? AND engram_id = ?
                        """,
                        (self.session_id, engram_id,)
                    )
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't delete an engram from the DB: {err}", exception=err)
                    return False

        def list_engrams(self):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        SELECT engram_id, actions, incident, somatic, incident_age FROM session_engrams WHERE session_id = ?
                        """,
                        (self.session_id,)
                    )
                    data = cur.fetchall()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't add an engram to the DB: {err}", exception=err)
                    return False
            
            parsed_data = []
            for engram in data:
                parsed_data.append({
                    "engram_id": engram[0],
                    "actions": engram[1],
                    "incident": engram[2],
                    "somatic": engram[3],
                    "incident_age": engram[4],
                })
            return parsed_data

        def get_session_details(self):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        SELECT session_id, preclear_cfid, date, summary, duration, auditor, remarks, status_code FROM sessions_list WHERE session_id = ?
                        """,
                        (self.session_id,)
                    )
                    data = cur.fetchone()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error while fetching all session actions for session ID {self.session_id}", exception=err)
                    return False
                
            if not data:
                return False
            
            return {
                "session_id": data[0],
                "preclear_cfid": data[1],
                "date": data[2],
                "summary": data[3],
                "duration": data[4],
                "auditor": data[5],
                "remarks": data[6],
                "status_code": data[7]
            }

        def list_planned_actions(self):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        SELECT action_id, action, completed FROM session_actions WHERE session_id = ?
                        """,
                        (self.session_id,)
                    )
                    data = cur.fetchall()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error while fetching all session actions for session ID {self.session_id}", exception=err)
                    return False

            parsed_data = []
            for row in data:
                parsed_data.append({
                    "session_id": self.session_id,
                    "action_id": row[0],
                    "action_text": row[1],
                    "completed": bool(row[2])
                })
            return parsed_data

        def add_engram(self, actions:str, incident:str, somatic:str, incident_age:int):
            session_id = self.session_id
            actions = str(actions)
            incident = str(incident)
            somatic = str(somatic)
            incident_age = int(incident_age)
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        INSERT INTO session_engrams (session_id, actions, incident, somatic, incident_age)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (session_id, actions, incident, somatic, incident_age)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't add an engram to the DB: {err}", exception=err)
                    return False
            return True

        def set_remarks_value(self, text_value:str):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        UPDATE sessions_list
                        SET remarks = ?
                        WHERE session_id = ?
                        """,
                        (text_value, self.session_id,)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Failed to update the session's saved remarks: {err}", exception=err)
                    return False
            return True

        def set_session_details(self, preclear_cfid, date, summary, duration, auditor):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        UPDATE sessions_list
                        SET date = ?, summary = ?, duration = ?, auditor = ?
                        WHERE session_id = ? AND preclear_cfid = ?
                        """,
                        (date, summary, duration, auditor, self.session_id, preclear_cfid)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Failed to set session details for the session: {err}", exception=err)
                    return False
            return True
        
        def delete_session(self):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        DELETE FROM sessions_list WHERE session_id = ?
                        """,
                        (self.session_id,)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Failed to delete the session {self.session_id}: {err}", exception=err)
                    return False
            return True

@router.get("/files/get/{cfid}/sessions")
@set_permission(["central_files", "dianetics"])
async def load_sessions_page(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has accessed the session records of {cfid}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    return templates.TemplateResponse(
        request,
        "sessions_list.html",
        {
            "profile": profile,
        }
    )

@router.get("/api/files/get/{cfid}/sessions/list_all")
@set_permission(["central_files", "dianetics"])
async def list_all_sessions(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has accessed the session records of {cfid}")
    
    all_sessions = AuditingLog.list_all_sessions(cfid)

    return JSONResponse(
        content=all_sessions,
        status_code=200
    )

@router.get("/api/files/get/{cfid}/sessions/create/{date}")
@set_permission(["central_files", "dianetics"])
async def create_session(request: Request, cfid:int, date:str):
    token:str = route_prechecks(request)
    username = authbook.token_owner(token)
    logbook.info(f"{request.client.host} ({username}) Has accessed the session records of {cfid}")
    
    try:
        cfid = int(cfid)
    except ValueError:
        return HTMLResponse(
            content={
                "error": "Incorrect cfid type. Expected INT"
            },
            status_code=400
        )
    try:
        date = datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return HTMLResponse(
            content={
                "error": "Incorrect date format. Expected str -> YYYY/MM/DD"
            },
            status_code=400
        )

    new_session_id = AuditingLog.new_session(
        date=date,
        cfid=cfid,
        auditor=username
    )

    return HTMLResponse(
        content=str(new_session_id),
        status_code=200
    )

@router.get("/files/get/{cfid}/sessions/{session_id}")
@set_permission(["central_files", "dianetics"])
async def load_sessions_page(request: Request, cfid, session_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has accessed to access the specific session {session_id} for {cfid}")
    
    try:
        session = AuditingLog.session(session_id=session_id)
    except LookupError:
        with open("modules/404.html", "r") as file:
            content = file.read()
        return HTMLResponse(content, status_code=404)

    profile = centralfiles.get_profile(cfid=int(cfid))
    session_data = session.get_session_details()

    status_map = {
        1: "completed",
        2: "scheduled",
        3: "cancelled"
    }
    text_status_code = status_map[session_data['status_code']]

    return templates.TemplateResponse(
        request,
        "session.html",
        context={
            "session": session_data,
            "profile": profile,
            "text_status_code": text_status_code
        }
    )

class set_details_data(BaseModel):
    date: str
    duration: int
    auditor: str
    summary: str

@router.post("/files/get/{cfid}/sessions/{session_id}/set_details")
@set_permission(["central_files", "dianetics"])
async def route_set_session_details(request: Request, cfid, session_id, data: set_details_data):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is setting details for the session {session_id} for CFID {cfid}")
    
    success = AuditingLog.session(session_id).set_session_details(
        preclear_cfid=cfid,
        date=data.date,
        summary=data.summary,
        duration=data.duration,
        auditor=data.auditor
    )

    return JSONResponse(
        content={
            "success": success,
        },
        status_code=200 if success else 500
    )

class set_remarks_data(BaseModel):
    text_value: str

@router.post("/api/files/get/{cfid}/sessions/{session_id}/set_remarks")
@set_permission(["central_files", "dianetics"])
async def route_set_session_details(request: Request, cfid, session_id, data: set_remarks_data):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is setting details for the session {session_id} for CFID {cfid}")

    success = AuditingLog.session(session_id).set_remarks_value(session_id, data.text_value)

    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 500
    )

class AddEngramData(BaseModel):
    actions: str
    incident: str
    somatic: str
    incident_age: int

@router.post("/api/files/get/{cfid}/sessions/{session_id}/add_engram")
@set_permission(["central_files", "dianetics"])
async def route_add_engram(request: Request, cfid, session_id, data: AddEngramData):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is setting details for the session {session_id} for CFID {cfid}")

    success = AuditingLog.session(session_id).add_engram(data.actions, data.incident, data.somatic, data.incident_age)

    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 500
    )

@router.get("/api/files/get/{cfid}/sessions/{session_id}/list_engrams")
@set_permission(["central_files", "dianetics"])
async def route_list_engrams(request: Request, cfid, session_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is setting details for the session {session_id} for CFID {cfid}")

    engrams = AuditingLog.session(session_id).list_engrams()

    return JSONResponse(
        content={
            "success": True,
            "engrams": engrams
        },
        status_code=200
    )

@router.delete("/api/files/get/{cfid}/sessions/{session_id}/delete_engram/{engram_id}")
@set_permission(["central_files", "dianetics"])
async def route_delete_engram(request: Request, cfid, session_id, engram_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is attempting to delete engram {engram_id} for session {session_id}, CFID {cfid}")
    success = AuditingLog.session(session_id=session_id).delete_engram(engram_id)
    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 500
    )

@router.delete("/api/files/get/{cfid}/delete/session/{session_id}")
@set_permission(["central_files", "dianetics"])
async def delete_session(request: Request, cfid, session_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is attempting to delete the session {session_id} for {cfid}")
    success = AuditingLog.session(session_id).delete_session()
    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 500
    )

@router.put("/api/files/get/{cfid}/session/set_status/{session_id}/{status_code}")
@set_permission(["central_files", "dianetics"])
async def session_set_status(request: Request, cfid, session_id:int, status_code:int):
    token:str = route_prechecks(request)
    valid_statuses = [
        1,  # Completed
        2,  # Pending
        3  # Cancelled
    ]
    if status_code not in valid_statuses:
        return JSONResponse(
            content={
                "success": False,
                "error": "Invalid status code, must be 1 (done), 2 (pending) or 3 (cancelled).",
            },
            status_code=400
        )

    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is attempting to mark session ID {session_id} as code {status_code} for {cfid}")
    success = AuditingLog.session(session_id).set_status(status_code)
    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 500
    )

@router.get("/api/files/get/{cfid}/sessions/{session_id}/list_actions")
@set_permission(["central_files", "dianetics"])
async def list_session_actions(request: Request, cfid, session_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) is listing planned actions for session {session_id} (CFID {cfid})")
    
    actions_list = AuditingLog.session(session_id).list_planned_actions()
    
    if actions_list is False:
        return JSONResponse(
            content={"success": False, "error": "Database query failed"},
            status_code=500
        )

    return JSONResponse(
        content={
            "success": True,
            "actions": actions_list
        },
        status_code=200
    )

class AddActionData(BaseModel):
    action_text: str

@router.post("/api/files/get/{cfid}/sessions/{session_id}/add_action")
@set_permission(["central_files", "dianetics"])
async def add_session_action(request: Request, cfid, session_id, data: AddActionData):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is adding an action for session {session_id}, CFID {cfid}")
    
    action_id = AuditingLog.session(session_id=session_id).add_action(data.action_text)

    return JSONResponse(
        content={
            "action_id": action_id
        },
        status_code=200
    )

class CompletedActionData(BaseModel):
    completed: bool

@router.post("/api/files/get/{cfid}/sessions/{session_id}/update_action/{action_id}")
@set_permission(["central_files", "dianetics"])
async def update_session_action(request: Request, cfid, session_id, action_id, data: CompletedActionData):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is adding an action for session {session_id}, CFID {cfid}")
    
    action_id = AuditingLog.session(session_id=session_id).set_action_status(data.completed, action_id=action_id)

    return JSONResponse(
        content={
            "action_id": action_id
        },
        status_code=200
    )

@router.delete("/api/files/get/{cfid}/sessions/{session_id}/delete_action/{action_id}")
@set_permission(["central_files", "dianetics"])
async def delete_session_action(request: Request, cfid, session_id, action_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is adding an action for session {session_id}, CFID {cfid}")
    
    session_id = int(session_id)
    cfid = int(cfid)
    action_id = int(action_id)

    success = AuditingLog.session(session_id).delete_action(action_id)

    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 400
    )

@router.get("/files/get/{cfid}/scheduling")
@set_permission(["central_files", "dianetics"])
async def open_scheduling_page(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is accessing the scheduling page for {cfid}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    return templates.TemplateResponse(
        request,
        "scheduling.html",
        context={
            "profile": profile
        }
    )

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def get_week_dates(reference_date=None):
    """
    Given reference_date, return list of 7 date objects (Mon-Sun) for the week containing the reference_date.
    """
    if reference_date is None:
        ref = datetime.datetime.now().date()
    elif isinstance(reference_date, datetime.datetime):
        ref = reference_date.date()
    elif isinstance(reference_date, str):
        ref = datetime.datetime.strptime(reference_date, "%Y-%m-%d").date()
    else:
        ref = reference_date

    # Calculate Monday of the week containing the reference date
    # weekday(): Monday=0, Sunday=6
    offset = ref.weekday()  # 0-6
    monday = ref - datetime.timedelta(days=offset)

    return [monday + datetime.timedelta(days=i) for i in range(7)]

def get_scheduling_data(cfid, reference_date=None):
    """
    Returns FULL WEEK (Monday\u2013Sunday) structured schedule data.
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # --- Get full week range ---
        week_dates = get_week_dates(reference_date)
        date_strings = [d.isoformat() for d in week_dates]

        # ------------------------------------------------------------------------------
        # 1. Fetch normal (non-repeating) schedules
        # ------------------------------------------------------------------------------
        cur.execute(
            f"""
            SELECT cfid, date, time_str, activity, auditor, room
            FROM dn_schedule_data
            WHERE cfid = ?
            AND DATE(date) IN ({','.join('?' * len(date_strings))})
            """,
            (cfid, *date_strings)
        )
        normal_schedules = cur.fetchall()

        # ------------------------------------------------------------------------------
        # 2. Fetch repeating schedules
        # ------------------------------------------------------------------------------
        cur.execute(
            """
            SELECT cfid, start_date, repeat_integer, end_date,
                   time_str, activity, auditor, room
            FROM dn_scheduling_data_repeating
            WHERE cfid = ?
            """,
            (cfid,)
        )
        repeating_schedules = cur.fetchall()

    # ------------------------------------------------------------------------------
    # Build frontend-ready result: every day present
    # ------------------------------------------------------------------------------
    output = { day: {} for day in DAY_NAMES }

    # Map ISO-date to weekday name
    date_to_day_name = { date_strings[i]: DAY_NAMES[i] for i in range(7) }

    # Helper to insert
    def insert(day_name, time_str, activity, auditor, room):
        output[day_name][time_str] = {
            "time": time_str,
            "activity": activity,
            "auditor": auditor,
            "room": room
        }

    # ------------------------------------------------------------------------------
    # Insert NORMAL schedules
    # ------------------------------------------------------------------------------
    for row in normal_schedules:
        date = row["date"].split(" ")[0]  # Cuts out all after the date
        day_name = date_to_day_name[date]
        insert(day_name, row["time_str"], row["activity"], row["auditor"], row["room"])

    # ------------------------------------------------------------------------------
    # Insert REPEATING schedules (expand)
    # ------------------------------------------------------------------------------
    for row in repeating_schedules:
        start = datetime.datetime.strptime(row["start_date"], "%Y-%m-%d").date()
        end = datetime.datetime.strptime(row["end_date"], "%Y-%m-%d").date()
        repeat_n = int(row["repeat_integer"])

        time_str = row["time_str"]
        activity = row["activity"]
        auditor = row["auditor"]
        room = row["room"]

        for d, iso in zip(week_dates, date_strings):
            if d < start or d > end:
                continue

            delta_days = (d - start).days
            if delta_days % repeat_n == 0:
                day_name = date_to_day_name[iso]
                insert(day_name, time_str, activity, auditor, room)

    return output

@router.get("/api/files/get/{cfid}/scheduling/fetch/week/{date}")
@set_permission(["central_files", "dianetics"])
async def open_scheduling_page(request: Request, cfid:int, date:str):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is accessing the set scheduling for {cfid}")

    try:
        dateobj = datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return JSONResponse(
            content={
                "error": "Date format invalid."
            },
            status_code=400
        )
    
    schedule_data = get_scheduling_data(cfid, dateobj)
    
    return JSONResponse(
        content=schedule_data,
        status_code=200
    )

class ScheduleCellData(BaseModel):
    cfid: int
    time: str
    activity: str = ""
    auditor: str = ""
    room: str

@router.post("/api/files/get/{cfid}/scheduling/save/cell/{day}")
@set_permission(["central_files", "dianetics"])
async def set_scheduling_cell(
    request: Request, 
    cfid: int, 
    day: str, 
    postdata: ScheduleCellData
):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) editing schedule for CFID {cfid} on {day}")

    if not postdata.activity and not postdata.auditor and not postdata.room:
        return JSONResponse(
            content={
                "success": False,
                "error": "You need to fill out at least activity, room or auditor key. They're not both required, but one must be present."
            }
        )

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }
    
    # Gets the start of the week we are currently in
    datenow = datetime.datetime.now()
    week_start = datenow - datetime.timedelta(days=datenow.weekday())
    set_for_day_date = week_start + datetime.timedelta(weekdays[day.lower()])

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Ensure only one entry per time + room per day
        cur.execute(
            """
            SELECT activity, auditor, room, schedule_id FROM dn_schedule_data
            WHERE cfid = ? AND time_str = ? AND room = ?
            """,
            (cfid, postdata.time, postdata.room)
        )
        data = cur.fetchone()
        existing = data is not None

        activity = postdata.activity
        auditor = postdata.auditor
        room = postdata.room

        if not activity:
            try:
                activity = data[0]
            except TypeError:
                activity = None
        if not auditor:
            try:
                auditor = data[1]
            except TypeError:
                auditor = None
        if not room:
            return JSONResponse(
                content={"success": False, "error": "You did not specify 'room' (str) key."}
            )

        if existing:
            schedule_id = data[3]
            # Update existing entry
            cur.execute(
                """
                UPDATE dn_schedule_data
                SET activity = ?, auditor = ?, date = ?
                WHERE schedule_id = ?
                """,
                (activity, auditor, set_for_day_date, schedule_id)
            )
            logbook.info(f"Updated schedule cell {schedule_id}")
        else:
            # Insert new entry
            cur.execute("""
                INSERT INTO dn_schedule_data (cfid, time_str, activity, date, auditor, room)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cfid, postdata.time, postdata.activity, set_for_day_date, postdata.auditor, postdata.room))
            logbook.info("Inserted new schedule cell")

        conn.commit()

    return JSONResponse({"success": True, "message": "Schedule cell saved successfully."}, 200)

@router.get("/files/get/{cfid}/flags")
@set_permission("central_files")
async def open_flags_page(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is accessing the file flags for {cfid}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    return templates.TemplateResponse(
        request,
        "flags.html",
        context={
            "profile": profile
        }
    )

# Note: Integration of below dianetics code may not be ideal. This was basically copy-pasted from the obsolete and deleted dianetics module.

class Dianetics_CF:
    @staticmethod
    def list_all_pcs():
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT cfid FROM cf_is_dianetics_pc WHERE is_dn_pc = True"
                )
                data = cursor.fetchall()
            except Exception as err:
                logbook.error(f"Error while fetching CF data: {err}", exception=err)
                return None

        parsed_data = []
        for item in data:
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT name FROM cf_names WHERE cfid = ?",
                        (item[0],)
                    )
                    pc_name = cursor.fetchone()[0]
                except Exception as err:
                    logbook.error(f"Error while fetching PC name: {err}", exception=err)
                    continue

            parsed_data.append({"cfid": item[0], "name": pc_name})
        return parsed_data

    @staticmethod
    def get_preclear_data(cfid):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM cf_names WHERE cfid = ?",
                    (cfid,)
                )
                pc_name = cursor.fetchone()[0]
            except Exception as err:
                logbook.error(f"Error while fetching PC data: {err}", exception=err)

        return {
            "cfid": cfid,
            "name": pc_name,
        }

@router.get("/api/dianetics/preclear/list")
@set_permission(permission="dianetics")
async def list_preclears(request: Request):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) Is listing all preclears.")

    all_pcs = Dianetics_CF.list_all_pcs()

    if all_pcs is not None:
        return JSONResponse(
            content=all_pcs,
            status_code=200,
        )
    else:
        return JSONResponse(
            content={"error": "Error while fetching PC data."},
            status_code=500
        )

# Dianometry section
chart_to_db_map = {
    "B. Dianetic Evaluation": "dianetic_evaluation",
    "C. BEHAVIOR AND PHYSIOLOGY": "behavior_and_physiology",
    "D. PSYCHATRIC RANGE": "psychiatric_range",
    "E. MEDICAL RANGE": "medical_range",
    "F. EMOTION": "emotion",
    "G. AFFINITY": "affinity",
    "H. SONIC": "comm_sonic",
    "I. VISIO": "comm_visio",
    "J. SOMATIC": "comm_somatic",
    "K. SPEECH: TALKS\nSPEECH: LISTENS": "comm_speech_talks_listens",
    "L. SUBJECT'S HANDLING OF WRITTEN OR SPOKEN COMM WHEN ACTING AS A RELAY POINT": "handling_of_comm_as_relay",
    "M. REALITY (AGREEMENT)": "reality",
    "N. CONDITION OF TRACK AND VALENCES": "condition_track_valences",
    "O. MANIFESTATION OF ENGRAMS AND LOCKS": "manifestation_engrams_and_locks",
    # Note. This is not "sexual behavior toward children" It is "Sexual behavior (Are they violent during it for example,) and their attitude toward children."
    "P. SEXUAL BEHAVIOR\nATTITUDE TOWARD CHILDREN.": "sexual_behavior_and_attitude_to_children",
    "Q. COMMAND OVER ENVIRONMENT": "command_over_environ",
    "R. ACTUAL WORTH TO SOCIETY COMPARED TO APPARENT WORTH": "actual_worth_apparent_worth",
    "S. ETHIC LEVEL": "ethics_level",
    "T. HANDLING OF TRUTH": "handling_of_truth",
    "U. COURAGE LEVEL": "courage_level",
    "V. ABILITY TO HANDLE RESPONSIBILITY": "ability_handle_responsibility",
    "W. PERSISTENCE ON A GIVEN COURSE": "persistence_given_course",
    "X. LITERALNESS OF RECEPTION OF STATEMENTS": "literlness_with_which_statements_are_received",
    "Y. METHOD USED BY SUBJECT TO HANDLE OTHERS": "method_handle_others",
    "Z. COMMAND VALUE OF ACTION PHRASES": "command_value_action_phrases",
    "AB. Present time.": "present_time",
    "AC. Straight Memory.": "straight_memory",
    "AD. PLEASURE MOMENTS.": "pleasure_moments",
    "AE. IMAGINARY INCIDENTS.": "TEWRBA_imaginary_incidents",
    "AF. LOCKS.": "TEWRBA_locks",
    "AG. SCANNING LOCKS.": "TEWRBA_scanning_locks",
    "AH. SECONDARY ENGRAMS.": "TEWRBA_secondaries",
    "AI. ENGRAMS.": "TEWRBA_engrams",
    "AJ. CHAINS OF ENGRAMS.": "TEWRBA_Chains_engrams",
    "AK. CIRCUITS.": "circuits",
    "AL. CONDITION OF FILE CLERK.": "condition_file_clerk",
    "AM. HYPNOTIC LEVEL": "hypnotic_level",
    "AN. LEVEL OF MIND ALERT.": "level_mind_alert",
    "AO. RELATIVE ENTHETA ON CASE (APPROXIMATIONS).": "relative_entheta_on_case",
    "AP. ABILITY TO EXPERIENCE PRESENT TIME PLEASURE": "ability_pc_experience_ptp_pleasure",
    "AQ. TONE LEVEL OF AUDITOR NECESSARY TO HANDLE CASE.": "auditor_tone_needed",
    "AR. HOW TO AUDIT THE CASE.": "how_audit_case"
}

chart_columns = chart_to_db_map.keys()

@router.get("/api/dianetics/dianometry/get-chart/{cfid}")
@set_permission(permission="dianetics")
async def get_chart(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(
        f"IP {request.client.host} ({authbook.token_owner(token)}) is fetching the chart data for CFID {cfid}."
    )

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM CF_hubbard_chard_of_eval WHERE cfid = ?",
                (cfid,)
            )
            row = cursor.fetchone()
            if not row:
                return JSONResponse([], status_code=200)

            data = row[1:]  # skip cfid column, take the rest as tone levels
    except Exception as err:
        logbook.error(f"Error while fetching chart data: {err}")
        return JSONResponse([], status_code=500)

    # Transform into an array of {column_name, tone_level}
    response_data = []
    for i, column_name in enumerate(chart_columns):
        tone_level = data[i] if i < len(data) else None
        response_data.append({
            "column_name": column_name,
            "tone_level": str(tone_level) if tone_level is not None else None
        })

    return JSONResponse(response_data, status_code=200)

class update_chart_data(BaseModel):
    cfid: str
    column_name: str
    tone_level: str

def calculate_new_ts_position(cfid):
    """
    Calculate a PC's tone level by taking all of their positions on the chart
    and returning the most common tone level.
    """
    # Get all tone level positions for the CFID
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM CF_hubbard_chard_of_eval WHERE cfid = ?",
            (cfid,)
        )
        row = cursor.fetchone()
        if not row:
            return None  # CFID not found

    # Convert row to a list of tone levels (skip cfid column)
    tone_levels = [row[i + 1] for i in range(len(chart_columns)) if row[i + 1] is not None]

    if not tone_levels:
        return None

    # Find the most common tone level
    counter = Counter(tone_levels)
    most_common_tone, _ = counter.most_common(1)[0]

    return float(most_common_tone)

def update_tonescale_estimation(cfid):
    new_ts_position = calculate_new_ts_position(cfid)
    if new_ts_position is not None:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO cf_tonescale_records (cfid, est_tone_level) VALUES (?, ?)
                    ON CONFLICT(cfid) DO UPDATE SET est_tone_level=excluded.est_tone_level
                    """,
                    (cfid, float(new_ts_position))
                )
                conn.commit()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while updating tone scale estimation: {err}", exception=err)
            conn.rollback()
            return
    else:
        logbook.warning(f"CFID {cfid} not found in CF_hubbard_chard_of_eval table.")

def get_can_handle_life(cfid):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT is_handleable FROM cf_pc_can_handle_life WHERE cfid = ?
                """,
                (cfid,)
            )
            can_handle_life = cur.fetchone()[0]
        except sqlite3.OperationalError as err:
            logbook.error(f"An error occured with getting if the PC can handle their life from the DB. Err: {err}", exception=err) 
            return False
        except TypeError:
            # No data
            return True

    return bool(can_handle_life)

def calculate_mind_class_estimation(cfid):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT sonic_shutoff, visio_shutoff FROM cf_dn_shutoffs WHERE cfid = ?",
                (cfid,)
            )
            data = cursor.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while fetching shutoffs: {err}", exception=err)
            conn.rollback()
            return None, None

        sonic_shutoff = bool(data[0]) if data[0] is not None else False
        visio_shutoff = bool(data[1]) if data[1] is not None else False

        try:
            cursor.execute(
                """
                SELECT dyn_1, dyn_2, dyn_3, dyn_4 FROM cf_dynamic_strengths WHERE cfid = ?
                """,
                (cfid,)
            )
            data = cursor.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while fetching dyn strengths: {err}", exception=err)
            conn.rollback()
            return None, None
        
        try:
            cursor.execute(
                """
                SELECT endowment FROM cf_pc_theta_endowments WHERE cfid = ?
                """,
                (cfid,)
            )
            endowment_data = cursor.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while fetching theta endowment for PC CFID {cfid}: {err}", exception=err)
            conn.rollback()
            return None, None
        
    theta_endowment = endowment_data[0] if endowment_data else 0

    # Defining traits of each class found in ./docs/mind_classes.md

    try:
        dyn_1 = data[0]
    except TypeError:
        dyn_1 = 0

    try:
        dyn_2 = data[1]
    except TypeError:
        dyn_2 = 0

    try:
        dyn_3 = data[2]
    except TypeError:
        dyn_3 = 0

    try:
        dyn_4 = data[3]
    except TypeError:
        dyn_4 = 0

    can_handle_life = get_can_handle_life(cfid)

    dynamics_score = (dyn_1 + dyn_2 + dyn_3 + dyn_4)
    if dynamics_score <= 5:
        apparent_class = 3  # Class C
    elif dynamics_score <= 6:
        apparent_class = 2 # Class B
    elif dynamics_score > 9:
        apparent_class = 1  # Class A
    else:
        logbook.warning(f"CFID {cfid} has a dynamics score of {dynamics_score} which is unexpected. Setting apparent class to 2.")
        apparent_class = 2  # Class B

    actual_class = apparent_class

    if sonic_shutoff and visio_shutoff:
        if apparent_class == 3:
            actual_class = 2
        elif apparent_class == 2:
            actual_class = 1
        else:
            actual_class = 1
    elif sonic_shutoff or visio_shutoff:
        if apparent_class == 3:
            actual_class = 2

    # theta has a range from 0 to 1000. A higher endowment improves mind class.
    # Low average is 200, Median average of your everyday human is 450, a HIGH average is 700+
    if theta_endowment >= 700:
        if dyn_3 == 3:  # if dyn 3 is great, they likely have a great tendency to lead. Indicating Class A
            actual_class = 1  # Class A
        else:
            if actual_class == 3:
                actual_class = 2  # Class B. Class C is unlikely with such a high endowment.
    elif theta_endowment >= 450:
        if actual_class == 3:
            actual_class = 2  # Class B. Class C is more likely with low endowment.
    elif theta_endowment < 350:
        if actual_class == 1:
            actual_class = 2  # Class B. Class A is unlikely with such a low endowment.
        elif actual_class == 2:
            actual_class = 3  # Class C
    elif theta_endowment <= 200:
        actual_class = 3  # Class C

    if can_handle_life:
        if actual_class != 1:
            actual_class = 2  # Class C Cannot handle life.
    else:
        if sonic_shutoff and visio_shutoff:
            apparent_class = 3  # Class C
        else:
            actual_class = 3  # Class C

    results = {
        "apparent": apparent_class,
        "actual": actual_class
    }

    return results

def update_mind_class_estimation(cfid):
    mind_class = calculate_mind_class_estimation(cfid)
    apparent_class = mind_class["apparent"]
    actual_class = mind_class["actual"]

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO cf_pc_mind_class (cfid, actual_class, apparent_class)
                VALUES (?, ?, ?)
                ON CONFLICT(cfid) DO UPDATE SET actual_class=excluded.actual_class, apparent_class=excluded.apparent_class
                """,
                (cfid, actual_class, apparent_class)
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while updating mind class estimation: {err}", exception=err)
            conn.rollback()
            return False

@router.post("/api/dianetics/dianometry/update-chart")
@set_permission(permission="dianetics")
async def update_chart(request: Request, data: update_chart_data):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is updating the chart data for CFID {data.cfid}, column {data.column_name}, tone level {data.tone_level}")

    if data.column_name not in chart_columns:
        return JSONResponse({"success": False, "error": "Invalid column name."}, status_code=400)

    column_name = chart_to_db_map[data.column_name]  # Convert to DB column name

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Note: Keep this secure and sanitised.
            cursor.execute(
                f"""
                INSERT INTO CF_hubbard_chard_of_eval (cfid, {column_name})
                VALUES (?, ?)
                ON CONFLICT(cfid) DO UPDATE SET {column_name}=excluded.{column_name}
                """,
                (data.cfid, data.tone_level)
            )
            conn.commit()

            update_tonescale_estimation(data.cfid)
            return JSONResponse({"success": True}, status_code=200)
    except sqlite3.OperationalError as err:
        logbook.error(f"Database error while updating chart data: {err}", exception=err)
        conn.rollback()
        return JSONResponse({"success": False, "error": "Database error occurred while updating chart data."}, status_code=500)

class dyn_strengths_data(BaseModel):
    cfid: int
    dynamic: str
    strength: str

dynamic_map = {
    "Self": 1,
    "Sex and Family": 2,
    "Groups": 3,
    "Mankind": 4
}

@router.post("/api/dianetics/dianometry/dyn_strengths/set")
@set_permission(permission="dianetics")
async def dyn_strengths(request: Request, data: dyn_strengths_data):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is setting dyn strengths for {data.cfid}.")

    dyn_strength = int(data.strength)
    dyn_number = dynamic_map[data.dynamic]

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO cf_dynamic_strengths (cfid, dyn_{dyn_number})
                VALUES (?, ?)
                ON CONFLICT(cfid) DO UPDATE SET dyn_{dyn_number}=excluded.dyn_{dyn_number}
                """,
                (data.cfid, dyn_strength,)
            )
            conn.commit()
            update_mind_class_estimation(data.cfid)
            return JSONResponse({"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while updating dyn strengths: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while updating dyn strengths."}, status_code=500)

@router.get("/api/dianetics/dianometry/dyn_strengths/get/{cfid}")
@set_permission(permission="dianetics")
async def get_dyn_strengths(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is getting all dyn strengths for {cfid}.")

    update_mind_class_estimation(cfid)

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT dyn_1, dyn_2, dyn_3, dyn_4 FROM cf_dynamic_strengths WHERE cfid = ?",
                (cfid,)
            )
            data = cur.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while fetching dyn strengths: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"error": "Database error occurred while fetching dyn strengths."}, status_code=500)

    if data is None:
        return JSONResponse([
            {"dynamic": 1, "strength": 0},
            {"dynamic": 2, "strength": 0},
            {"dynamic": 3, "strength": 0},
            {"dynamic": 4, "strength": 0}
        ], status_code=200)

    parsed_data = []
    dyn_counter = 0
    for dynamic in data:
        dyn_counter += 1
        parsed_data.append({
            "dynamic": dyn_counter,
            "strength": dynamic if dynamic else 0
        })
    return JSONResponse(parsed_data, status_code=200)

class shutoffs_data(BaseModel):
    cfid: int
    name: str
    state: bool

@router.post("/api/dianetics/dianometry/shutoffs/set")
@set_permission(permission="dianetics")
async def set_shutoffs(request: Request, data: shutoffs_data):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is setting shutoff {data.name} for {data.cfid} to {data.state}.")

    update_mind_class_estimation(data.cfid)

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO cf_dn_shutoffs (cfid, {data.name}_shutoff)
                VALUES (?, ?)
                ON CONFLICT(cfid) DO UPDATE SET {data.name}_shutoff=excluded.{data.name}_shutoff
                """,
                (data.cfid, data.state,)
            )
            conn.commit()
            return JSONResponse({"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while updating shutoffs: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while updating shutoffs."}, status_code=500)

@router.get("/api/dianetics/dianometry/shutoffs/get/{cfid}")
@set_permission(permission=["dianetics", "central_files"])
async def get_shutoffs(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is getting all shutoffs for {cfid}.")

    try:
        # We update it here and now incase the values were changed elsewhere
        update_mind_class_estimation(cfid)
    except Exception as err:
        logbook.error(f"Error while updating mind class estimation: {err}", exception=err)

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT sonic_shutoff, visio_shutoff FROM cf_dn_shutoffs WHERE cfid = ?",
                (cfid,)
            )
            data = cur.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while fetching shutoffs: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"error": "Database error occurred while fetching shutoffs."}, status_code=500)

    try:
        sonic_shutoff = bool(data[0])
    except TypeError:
        sonic_shutoff = False
    try:
        visio_shutoff = bool(data[1])
    except TypeError:
        visio_shutoff = False

    return JSONResponse([
        {"name": "sonic", "state": sonic_shutoff},
        {"name": "visio", "state": visio_shutoff}
    ], status_code=200)

mind_level_map = {
    1: "Class A",
    2: "Class B",
    3: "Class C"
}

@router.get("/api/dianetics/dianometry/get_mind_class/{cfid}")
@set_permission(permission=["dianetics", "central_files"])
async def get_mind_class(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is getting mind class for {cfid}.")
    # Very often when getting mind class, other values have changed. So we update it here.
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT actual_class, apparent_class FROM cf_pc_mind_class WHERE cfid = ?",
                (cfid,)
            )
            data = cur.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while fetching mind class: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"error": "Database error occurred while fetching mind class."}, status_code=500)

    if not data:
        return JSONResponse({"error": "Mind class not found."}, status_code=404)
    else:
        return JSONResponse({
            "actual": mind_level_map[int(data[0])],
            "apparent": mind_level_map[int(data[1])]
            },
            status_code=200
        )