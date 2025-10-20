from fastapi.responses import HTMLResponse, JSONResponse
from library.auth import require_prechecks, authbook
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from library.authperms import set_permission
from library.logbook import LogBookHandler
from library.database import DB_PATH
from collections import Counter
from pydantic import BaseModel
import sqlite3
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("DIANETICS")

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

@router.get("/dianetics", response_class=HTMLResponse)
@set_permission(permission="dianetics")
async def show_index(request: Request, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) has accessed the dianetics page.")
    return templates.TemplateResponse(request, "dianetics.html")

@router.get("/api/dianetics/preclear/list")
@set_permission(permission="dianetics")
async def list_preclears(request: Request, token: str = Depends(require_prechecks)):
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

@router.get("/dianetics/dianometry/{cfid}", response_class=HTMLResponse)
@set_permission(permission="dianetics")
async def show_dianometry(request: Request, cfid:int, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) has accessed the dianometry page.")

    preclear = Dianetics_CF.get_preclear_data(cfid)

    return templates.TemplateResponse(
        request,
        "dianometry_profile.html",
        {
            "preclear": preclear,
        }
    )

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
async def get_chart(request: Request, cfid, token: str = Depends(require_prechecks)):
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

        sonic_shutoff = data[0] if data[0] is not None else False
        visio_shutoff = data[1] if data[1] is not None else False

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
        dyn_1 = data[0]
        if isinstance(dyn_1, None):
            raise TypeError
    except TypeError:
        dyn_1 = 0

    try:
        dyn_2 = data[1]
        if isinstance(dyn_2, None):
            raise TypeError
    except TypeError:
        dyn_2 = 0

    try:
        dyn_3 = data[2]
        if isinstance(dyn_3, None):
            raise TypeError
    except TypeError:
        dyn_3 = 0

    try:
        dyn_4 = data[3]
        if isinstance(dyn_4, None):
            raise TypeError
    except TypeError:
        dyn_4 = 0

    dynamics_score = (dyn_1 + dyn_2 + dyn_3 + dyn_4)
    if dynamics_score <= 5:
        apparent_class = 3  # Class C
    elif dynamics_score <= 10:
        apparent_class = 2 # Class B
    else:
        apparent_class = 1  # Class A

    if sonic_shutoff and visio_shutoff:
        actual_class = apparent_class
        if apparent_class == 3:
            actual_class = 2
        if apparent_class == 2 and dynamics_score >= 7:
            actual_class = 1
    else:
        actual_class = apparent_class

    return {
        "apparent": apparent_class,
        "actual": actual_class
    }

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
async def update_chart(request: Request, data: update_chart_data, token: str = Depends(require_prechecks)):
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
async def dyn_strengths(request: Request, data: dyn_strengths_data, token: str = Depends(require_prechecks)):
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
async def get_dyn_strengths(request: Request, cfid, token: str = Depends(require_prechecks)):
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
async def set_shutoffs(request: Request, data: shutoffs_data, token: str = Depends(require_prechecks)):
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
@set_permission(permission="dianetics")
async def get_shutoffs(request: Request, cfid, token: str = Depends(require_prechecks)):
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
@set_permission(permission="dianetics")
async def get_mind_class(request: Request, cfid, token: str = Depends(require_prechecks)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is getting mind class for {cfid}.")
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