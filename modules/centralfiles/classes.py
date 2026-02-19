from library.logbook import LogBookHandler
from library.auth import authbook
import datetime
import sqlite3

logbook = LogBookHandler("Central Files")
DB_PATH = "data.sqlite"

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
                "chem_assist": on_chem_assist,
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
            except sqlite3.OperationalError as err:
                logbook.error("Error updating name!", exception=err)
                conn.rollback()
                return False
            finally:
                conn.close()

        def first_name(self, name):
            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE cf_names
                    SET first_name = ?
                    WHERE cfid = ?
                    """,
                    (name, self.cfid)
                )
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.OperationalError as err:
                logbook.error("Error updating first name!", exception=err)
                conn.rollback()
                return False
            finally:
                conn.close()


        def middle_name(self, name):
            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE cf_names
                    SET middle_name = ?
                    WHERE cfid = ?
                    """,
                    (name, self.cfid)
                )
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.OperationalError as err:
                logbook.error("Error updating middle name!", exception=err)
                conn.rollback()
                return False
            finally:
                conn.close()


        def last_name(self, name):
            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE cf_names
                    SET last_name = ?
                    WHERE cfid = ?
                    """,
                    (name, self.cfid)
                )
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.OperationalError as err:
                logbook.error("Error updating last name!", exception=err)
                conn.rollback()
                return False
            finally:
                conn.close()

        def alias(self, alias):
            conn = sqlite3.connect(DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE cf_names
                    SET alias = ?
                    WHERE cfid = ?
                    """,
                    (alias, self.cfid)
                )
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.OperationalError as err:
                logbook.error("Error updating alias!", exception=err)
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
    def get_cfid_by_email(email_address:str):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT cfid FROM cf_pc_contact_details WHERE email_addr = ?",
                    (email_address,)
                )
                data = cursor.fetchone()
                if data:
                    return data[0]
                else:
                    return None
            except sqlite3.OperationalError as err:
                logbook.error(f"Error getting the CFID for email {email_address}: {err}", exception=err)
                return None

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
    def add_name(first_name:str=None, last_name:str=None, middle_name:str=None, alias:str=None, profile_type:str = None, staff_username=None):
        """
        Docstring for add_name
        
        :param name: The full name for the person being added
        :param staff_username: If the user is staff, enter their username and we'll assosciate the username with the person.
        """
        conn = sqlite3.connect(DB_PATH)

        if not profile_type.lower() in ['individual', 'company', 'group leader']:
            raise ValueError(f"fInvalid profile type for name {first_name}, alias {alias}: {profile_type}")

        if not alias:
            if not first_name:
                raise ValueError("No first name entered!")
            name = first_name
            if middle_name:
                name += f" {middle_name}"
            if last_name:
                name += f" {last_name}"
        else:
            name = alias

        try:
            cursor = conn.cursor()
            if not alias:
                cursor.execute(
                    """
                    INSERT INTO cf_names (name, first_name, middle_name, last_name) VALUES (?, ?, ?, ?)
                    """,
                    (name, first_name, middle_name, last_name),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO cf_names (name, alias) VALUES (?, ?)
                    """,
                    (name, alias),
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
                (cfid, "Unknown Occupation")
            )
            cursor.execute(
                """
                INSERT INTO cf_name_types (cfid, nametype) VALUES (?, ?)
                """,
                (cfid, profile_type)
            )

            conn.commit()
            return cfid
        except sqlite3.OperationalError as err:
            logbook.error("Error adding a name!", err)
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
            
            # Names
            try:
                cursor.execute(
                    """
                    SELECT first_name, middle_name, last_name, alias FROM cf_names WHERE cfid = ?
                    """,
                    (cfid,)
                )
                data = cursor.fetchone()
                first_name = data[0]
                middle_name = data[1]
                last_name = data[2]
                alias = data[3]
            except sqlite3.OperationalError as err:
                logbook.error(f"Error getting the names for cfid {cfid}: {err}", exception=err)
                conn.rollback()
                first_name = "ERR_FETCHING"
                middle_name = "ERR_FETCHING"
                last_name = "ERR_FETCHING"
                alias = "ERR_FETCHING"
            except TypeError:
                first_name = "ERR_FETCHING"
                middle_name = "ERR_FETCHING"
                last_name = "ERR_FETCHING"
                alias = "ERR_FETCHING"

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
            "is_staff": authbook.check_exists(cfid=cfid),
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "alias": alias
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