from library.logbook import LogBookHandler
import logging
import sqlite3

DB_PATH = "data.sqlite"
logbook = LogBookHandler('DB Manager')

class database:
    @staticmethod
    def modernize():
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
            },
            "finance_transactions": {
                "transaction_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "account_id": "INTEGER NOT NULL REFERENCES finance_accounts(account_id)",
                "amount": "REAL NOT NULL",
                "is_expense": "BOOLEAN NOT NULL",
                "description": "TEXT NOT NULL",
                "date": "DATE NOT NULL DEFAULT CURRENT_DATE",
                "time": "TIME NOT NULL DEFAULT CURRENT_TIME",
            },
            "transaction_receipts": {
                "transaction_id": "INTEGER NOT NULL REFERENCES transactions(transaction_id)",
                # A photo of the receipt
                "receipt": "BLOB NOT NULL",
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