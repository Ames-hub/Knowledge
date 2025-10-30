from library.logbook import LogBookHandler
import logging
import sqlite3

DB_PATH = "data.sqlite"
logbook = LogBookHandler('DB Manager')

class database:
    @staticmethod
    def modernize() -> None:
        """
        This function is used to modernise the database to the current version. It will check if the tables exist, and
        if they don't, it will create them. If the tables do exist, it will check if the columns are up to date, and if
        they aren't, it will update them.

        :return:
        """
        # Function I pulled from another project.
        # Using this dict, it formats the SQL query to create the tables if they don't exist

        table_dict = {
            'authbook': {
                'username': 'TEXT PRIMARY KEY',
                'password': 'TEXT NOT NULL',
                'arrested': 'BOOLEAN NOT NULL DEFAULT FALSE',
            },
            'auth_permissions': {
                'entry_id': 'INTEGER PRIMARY KEY AUTOINCREMENT',  # Just for easy editing in DB viewers
                'username': 'TEXT NOT NULL',
                'permission': 'TEXT NOT NULL',
                'allowed': 'BOOLEAN NOT NULL DEFAULT TRUE',
            },
            'revoked_tokens': {
                'token': 'TEXT NOT NULL PRIMARY KEY',
                'revoked_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
            },
            'user_sessions': {
                'username': 'TEXT',
                'token': 'TEXT NOT NULL PRIMARY KEY',
                'created_at': 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP',
                'expires_at': 'DATETIME NOT NULL',
            },
            "cf_names": {
                "cfid": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Must add a name before anything else can be done
                "name": "TEXT NOT NULL",
            },
            "cf_ages": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "age": "INTEGER NOT NULL",
            },
            "cf_pronouns": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "subjective": "TEXT NOT NULL",
                "objective": "TEXT NOT NULL",
            },
            "cf_profile_notes": {
                "note_id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Cannot use cfid ID for this as cfid will not be unique here
                "cfid": "INTEGER NOT NULL",  # cfid here is a grouping-per-person attribute.
                "note": "TEXT NOT NULL",
                "add_date": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
                "author": "TEXT NOT NULL",
            },
            "cf_contact_details": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "address": "TEXT NOT NULL",
                "phone": "TEXT NOT NULL",
                "email": "TEXT NOT NULL",
            },
            "cf_is_dianetics_pc": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "is_dn_pc": "BOOLEAN NOT NULL DEFAULT FALSE",
            },
            "cf_dn_stuck_case": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "is_stuck_case": "BOOLEAN NOT NULL DEFAULT FALSE",
                "stuck_age": "INT NOT NULL DEFAULT -1"  # If stuck, where? Age 3?
            },
            "cf_dn_control_case": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "is_control_case": "BOOLEAN NOT NULL DEFAULT FALSE",
            },
            "cf_dn_shutoffs": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "sonic_shutoff": "BOOLEAN NOT NULL DEFAULT FALSE",
                "visio_shutoff": "BOOLEAN NOT NULL DEFAULT FALSE",
            },
            "cf_dn_fabricator_case": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "is_fabricator_case": "BOOLEAN NOT NULL DEFAULT FALSE",
            },
            "cf_dn_action_records": {
                "action_id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Mostly here so it can be modified in DB viewers
                "date": "DATE NOT NULL DEFAULT CURRENT_DATE",
                "cfid": "INTEGER NOT NULL",
                "action": "TEXT NOT NULL",
            },
            "cf_tonescale_records": {
                "cfid": "INTEGER NOT NULL PRIMARY KEY",
                "est_tone_level": "REAL NOT NULL",
            },
            "cf_pc_mind_class": {
                "cfid": "INTEGER NOT NULL PRIMARY KEY",
                "actual_class": "INT NOT NULL",  # Class A, B or C. Store as int (1 = A, 2 = B, 3 = C)
                "apparent_class": "INT NOT NULL",
            },
            "bulletin_archives": {
                "archive_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "title": "TEXT NOT NULL",
                "content": "TEXT NOT NULL",
                "owner": "TEXT NOT NULL",
                "tags": "TEXT"
            },
            "finance_accounts": {
                "account_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "account_name": "TEXT NOT NULL",
                "balance": "REAL NOT NULL DEFAULT 0.0",
                "owner": "TEXT"
            },
            "finance_transactions": {
                "transaction_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "account_id": "INTEGER NOT NULL",
                "amount": "REAL NOT NULL",
                "is_expense": "BOOLEAN NOT NULL",
                "description": "TEXT NOT NULL",
                "date": "DATE NOT NULL DEFAULT CURRENT_DATE",
                "time": "TIME NOT NULL DEFAULT CURRENT_TIME",
            },
            "transaction_receipts": {
                "transaction_id": "INTEGER NOT NULL",
                # A photo of the receipt
                "receipt": "BLOB NOT NULL",
                "receipt_mimetype": "TEXT NOT NULL",
            },
            "fp_expenses": {
                "name": "TEXT NOT NULL PRIMARY KEY",
                "amount": "REAL NOT NULL",
                "frequency": "INT NOT NULL",
                "annual_cost": "REAL NOT NULL",
            },
            "debts": {
                "debt_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "debtor": "TEXT NOT NULL",
                "debtee": "TEXT NOT NULL",
                "amount": "REAL NOT NULL",
                "start_date": "DATE NOT NULL DEFAULT CURRENT_DATE",
                "end_date": "DATE",
                "cfid": "INT",  # The Central Files ID for whom this debt is for.
            },
            "debt_records": {
                "record_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "debt_id": "INTEGER NOT NULL",
                "start_date": "DATE NOT NULL DEFAULT CURRENT_DATE",
                "amount": "REAL NOT NULL",
                "description": "TEXT NOT NULL",
                "paid_off": "BOOLEAN NOT NULL DEFAULT FALSE",
            },
            "battleplans": {
                "bp_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "date": "DATE NOT NULL DEFAULT CURRENT_DATE",
                "owner": "TEXT NOT NULL",
            },
            "bp_tasks": {
                "task_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "date": "DATE NOT NULL",
                "task": "TEXT NOT NULL",
                "is_done": "BOOLEAN NOT NULL DEFAULT FALSE",
                "owner": "TEXT NOT NULL",
                "category": "TEXT NOT NULL DEFAULT 'Other'",
            },
            "bp_quotas": {
                "quota_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "bp_id": "INT NOT NULL",
                "bp_date": "DATE NOT NULL",
                "planned_amount": "REAL NOT NULL DEFAULT 0.0",
                "done_amount": "REAL NOT NULL DEFAULT 0.0",
                "owner": "TEXT NOT NULL",
                "name": "TEXT NOT NULL",
                "weekly_target": "REAL NOT NULL DEFAULT 0.0",
            },
            "invoices": {
                "invoice_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "date": "DATE NOT NULL DEFAULT CURRENT_DATE",
                "amount": "REAL NOT NULL",
                "is_paid": "BOOLEAN NOT NULL DEFAULT FALSE",
                "cfid": "INT",  # The Central Files ID for whom this invoice is for.
                "billing_name": "TEXT NOT NULL DEFAULT ''",
                "billing_address": "TEXT NOT NULL DEFAULT ''",
                "billing_email_address": "TEXT NOT NULL DEFAULT ''",
                "billing_phone": "TEXT NOT NULL DEFAULT ''",
                "billing_notes": "TEXT NOT NULL DEFAULT ''",
            },
            "items_on_invoices": {
                # Items that ARE on an invoice, and which invoice.
                "itemkey": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Purely for being able to modify this table in beekeeper studio.
                "invoice_id": "INTEGER NOT NULL",
                "item": "TEXT NOT NULL",
                "value": "REAL NOT NULL",
            },
            "invoice_items": {
                # Items that COULD appear on an invoice.
                "item_id": "TEXT PRIMARY KEY",  # A service, like "Washed windows" or whatever.
                "value": "REAL NOT NULL",
            },
            "CF_hubbard_chard_of_eval": {  # Credit to L. Ron Hubbard for his work on this.
                "cfid": "INT NOT NULL PRIMARY KEY",
                "dianetic_evaluation": "INT",
                "behavior_and_physiology": "INT",
                "psychiatric_range": "INT",
                "medical_range": "INT",
                "emotion": "INT",
                "affinity": "INT",
                "comm_sonic": "INT",
                "comm_visio": "INT",
                "comm_somatic": "INT",
                "comm_speech_talks_listens": "INT",
                "handling_of_comm_as_relay": "INT",
                "reality": "INT",
                "condition_track_valences": "INT",
                "manifestation_engrams_and_locks": "INT",
                "sexual_behavior_and_attitude_to_children": "INT",
                "attitude_to_children": "INT",
                "command_over_environ": "INT",
                "actual_worth_apparent_worth": "INT",
                "ethics_level": "INT",
                "handling_of_truth": "INT",
                "courage_level": "INT",
                "ability_handle_responsibility": "INT",
                "persistence_given_course": "INT",
                "literlness_with_which_statements_are_received": "INT",
                "method_handle_others": "INT",
                "command_value_action_phrases": "INT",
                "present_time": "INT",
                "straight_memory": "INT",
                "pleasure_moments": "INT",
                # TEWRBA = "Types of Entheta Which can be Run on Preclear by Auditor"
                "TEWRBA_imaginary_incidents": "INT",
                "TEWRBA_locks": "INT",
                "TEWRBA_scanning_locks": "INT",
                "TEWRBA_secondaries": "INT",
                "TEWRBA_engrams": "INT",
                "TEWRBA_Chains_engrams": "INT",
                "circuits": "INT",
                "condition_file_clerk": "INT",
                "hypnotic_level": "INT",
                "level_mind_alert": "INT",
                "relative_entheta_on_case": "INT",
                "ability_pc_experience_ptp_pleasure": "INT",
                "auditor_tone_needed": "INT",
                "how_audit_case": "INT"
            },
            "cf_dynamic_strengths": {
                "cfid": "INT NOT NULL PRIMARY KEY",
                "dyn_1": "INT",
                "dyn_2": "INT",
                "dyn_3": "INT",
                "dyn_4": "INT",  # The int is strength. 1 = Weak, 2 = Normal, 3 = Strong.
            },
            "signalserver_items": {
                "signal_route": "TEXT NOT NULL PRIMARY KEY",
                "http_code":  "INT NOT NULL DEFAULT 200",
                "html_response": "TEXT NOT NULL DEFAULT 'No Response Set'",
                "is_closed": "BOOLEAN NOT NULL DEFAULT FALSE",
            },
            "cf_profile_images": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "image": "BLOB NOT NULL",
            },
            "cf_occupations": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "occupation": "TEXT NOT NULL",
            },
            "cf_dates_of_birth": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "date_of_birth": "DATE NOT NULL DEFAULT '01/01/1950'"
            },
            # Theta endowment is a number measuring how "big" a person is basically.
            # For instance, a being with a theta endowment of 1000 could witness an awful atrocity and still be able to solve problems rationally,
            # And is awful hard to upset.
            "cf_pc_theta_endowments": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "endowment": "INT NOT NULL DEFAULT 0"
            },
            "cf_pc_can_handle_life": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                "is_handleable": "BOOLEAN NOT NULL DEFAULT TRUE"
            },
            "cf_agreements": {
                "agreement_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "cfid": "INTEGER NOT NULL",
                "agreement": "TEXT NOT NULL",
                "date_of_agreement": "DATE NOT NULL",
                "fulfilled": "BOOLEAN NOT NULL DEFAULT FALSE"
            },
            "sessions_list": {
                "session_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "preclear_cfid": "INTEGER NOT NULL",  # Who the session was for
                "date": "DATE NOT NULL",
                "summary": "TEXT NOT NULL",
                "duration": "INTEGER NOT NULL",  # In minutes
                "auditor": "TEXT NOT NULL",
                "remarks": "TEXT NOT NULL DEFAULT 'No recorded remarks'"
            },
            "session_actions": {
                "action_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "session_id": "INTEGER NOT NULL",
                "action": "TEXT NOT NULL",
                "completed": "BOOLEAN NOT NULL"
            },
            "session_engrams": {
                "engram_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "session_id": "INTEGER NOT NULL",
                "actions": "TEXT NOT NULL",
                "incident": "TEXT NOT NULL",
                "somatic": "TEXT NOT NULL",
                "incident_age": "INTEGER NOT NULL"
            },
            "cf_chem_assist": {
                "cfid": "INTEGER PRIMARY KEY NOT NULL",
                # A 'chemical assist' is just vitamins and minerals and stuff needed to survive. It helps with Auditing.
                "on_chem_assist": "BOOLEAN NOT NULL DEFAULT FALSE"
            },
            "schedule_data": {
                "schedule_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "cfid": "INTEGER NOT NULL",
                "date": "DATE NOT NULL",
                "time_str": "TEXT NOT NULL",
                "activity": "TEXT NOT NULL",
                "auditor": "TEXT NOT NULL",
                "room": "TEXT NOT NULL"
            }
        }
        
        for table_name, columns in table_dict.items():
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(f'''
                        SELECT name
                        FROM sqlite_master
                        WHERE type='table' AND name='{table_name}';
                    ''')
                table_exist = cur.fetchone() is not None

            # If the table exists, check and update columns
            if table_exist:
                for column_name, column_properties in columns.items():
                    # Check if the column exists
                    cur.execute(f'''
                            PRAGMA table_info({table_name});
                        ''')
                    columns_info = cur.fetchall()
                    column_exist = any(column_info[1] == column_name for column_info in columns_info)

                    # If the column doesn't exist, add it
                    if not column_exist:
                        try:
                            cur.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_properties};')
                        except sqlite3.OperationalError as err:
                            print(f"ERROR EDITING TABLE {table_name}, ADDING COLUMN {column_name} {column_properties}")
                            raise err

            # If the table doesn't exist, create it with columns
            else:
                columns_str = ', '.join(
                    [f'{column_name} {column_properties}' for column_name, column_properties in columns.items()]
                )
                try:
                    cur.execute(f'CREATE TABLE {table_name} ({columns_str});')
                except sqlite3.OperationalError as err:
                    print(f"There was a problem creating the table {table_name} with columns {columns_str}")
                    logging.error(f"An error occurred while creating the table {table_name} with columns {columns_str}", err)
                    exit(1)