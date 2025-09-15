from fastapi.responses import HTMLResponse, JSONResponse
from library.auth import require_valid_token, authbook
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
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
                logbook.error(f"Error while fetching CF data: {err}")
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
                    logbook.error(f"Error while fetching PC name: {err}")
                    continue

            parsed_data.append({"cfid": item[0], "name": pc_name})
        return parsed_data

@router.get("/dianetics", response_class=HTMLResponse)
async def show_index(request: Request, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) has accessed the dianetics page.")
    return templates.TemplateResponse(request, "dianetics.html")

@router.get("/api/dianetics/preclear/list")
async def list_preclears(request: Request, token: str = Depends(require_valid_token)):
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

@router.get("/dianetics/dianometry", response_class=HTMLResponse)
async def show_dianometry(request: Request, token: str = Depends(require_valid_token)):
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) has accessed the dianometry page.")
    return templates.TemplateResponse(request, "dianometry.html")

chart_columns = [
    "1. BEHAVIOR AND PHYSIOLOGY",
    "2. MEDICAL RANGE",
    "3. EMOTION",
    "4. SEXUAL BEHAVIOR",
    "5. ATTITUDE TOWARD CHILDREN",
    "6. COMMAND OVER ENVIRONMENT",
    "7. ACTUAL WORTH TO SOCIETY COMPARED TO APPARENT WORTH",
    "8. ETHIC LEVEL",
    "9. HANDLING OF TRUTH",
    "10. COURAGE LEVEL",
    "11. SPEECH: TALKS",
    "SPEECH: LISTENS",
    "12. SUBJECT'S HANDLING OF WRITTEN OR SPOKEN COMM WHEN ACTING AS A RELAY POINT",
    "13. REALITY (AGREEMENT)",
    "14. ABILITY TO HANDLE RESPONSIBILITY",
    "15. PERSISTENCE ON A GIVEN COURSE",
    "16. LITERALNESS OF RECEPTION OF STATEMENTS",
    "17. METHOD USED BY SUBJECT TO HANDLE OTHERS",
    "18. HYPNOTIC LEVEL",
    "19. ABILITY TO EXPERIENCE PRESENT TIME PLEASURE",
    "20. YOUR VALUE AS A FRIEND",
    "21. HOW MUCH OTHERS LIKE YOU",
    "22. STATE OF YOUR POSSESSIONS",
    "23. HOW WELL ARE YOU UNDERSTOOD",
    "24. POTENTIAL SUCCESS",
    "25. POTENTIAL SURVIVAL"
]

chart_to_db_map = {
    "1. BEHAVIOR AND PHYSIOLOGY": "behavior_and_psychology",
    "2. MEDICAL RANGE": "medical_range",
    "3. EMOTION": "emotion",
    "4. SEXUAL BEHAVIOR": "sexual_behavior",
    "5. ATTITUDE TOWARD CHILDREN": "attitude_children",
    "6. COMMAND OVER ENVIRONMENT": "command_over_environ",
    "7. ACTUAL WORTH TO SOCIETY COMPARED TO APPARENT WORTH": "worth_actual_apparent",
    "8. ETHIC LEVEL": "ethics_level",
    "9. HANDLING OF TRUTH": "handling_of_truth",
    "10. COURAGE LEVEL": "courage_level",
    "11. SPEECH: TALKS": "speech_talks",
    "SPEECH: LISTENS": "speech_listens",
    "12. SUBJECT'S HANDLING OF WRITTEN OR SPOKEN COMM WHEN ACTING AS A RELAY POINT": "handling_of_comm_as_relay",
    "13. REALITY (AGREEMENT)": "reality",
    "14. ABILITY TO HANDLE RESPONSIBILITY": "responsibility",
    "15. PERSISTENCE ON A GIVEN COURSE": "persistence",
    "16. LITERALNESS OF RECEPTION OF STATEMENTS": "literalness_of_reception",
    "17. METHOD USED BY SUBJECT TO HANDLE OTHERS": "method_handling_others",
    "18. HYPNOTIC LEVEL": "hypnotic_level",
    "19. ABILITY TO EXPERIENCE PRESENT TIME PLEASURE": "ability_to_experience_pt_pleasure",
    "20. YOUR VALUE AS A FRIEND": "value_as_friend",
    "21. HOW MUCH OTHERS LIKE YOU": "how_much_others_like",
    "22. STATE OF YOUR POSSESSIONS": "state_of_possessions",
    "23. HOW WELL ARE YOU UNDERSTOOD": "how_well_understood",
    "24. POTENTIAL SUCCESS": "potential_success",
    "25. POTENTIAL SURVIVAL": "potential_survival"
}

@router.get("/api/dianetics/dianometry/get-chart/{cfid}")
async def get_chart(request: Request, cfid, token: str = Depends(require_valid_token)):
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

    dyn_1 = data[0] if data[0] is not None else 0
    dyn_2 = data[1] if data[1] is not None else 0
    dyn_3 = data[2] if data[2] is not None else 0
    dyn_4 = data[3] if data[3] is not None else 0

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
async def update_chart(request: Request, data: update_chart_data, token: str = Depends(require_valid_token)):
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
async def dyn_strengths(request: Request, data: dyn_strengths_data, token: str = Depends(require_valid_token)):
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
async def get_dyn_strengths(request: Request, cfid, token: str = Depends(require_valid_token)):
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
async def set_shutoffs(request: Request, data: shutoffs_data, token: str = Depends(require_valid_token)):
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
async def get_shutoffs(request: Request, cfid, token: str = Depends(require_valid_token)):
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
async def get_mind_class(request: Request, cfid, token: str = Depends(require_valid_token)):
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
