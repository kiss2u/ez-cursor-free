import sqlite3
import os
import sys
from logger import logging


class CursorAuthManager:
    def __init__(self):
        if os.name == "nt":  # Windows
            appdata = os.getenv("APPDATA")
            if appdata is None:
                raise EnvironmentError("not.set.environment.variable.APPDATA")
            self.db_path = os.path.join(
                appdata, "Cursor", "User", "globalStorage", "state.vscdb"
            )
        elif os.name == 'posix':  # Linux or macOS
            if os.uname().sysname == 'Darwin':
                self.db_path = os.path.expanduser(
                    "~/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
                )
            else:  # Linux
                self.db_path = os.path.expanduser(
                    "~/.config/Cursor/User/globalStorage/state.vscdb"
                )
        else:
            raise NotImplementedError('os.not.supported: {sys.platform}')

        logging.info(f"auth.db.path: {self.db_path}")
            

    def update_auth(self, email=None, access_token=None, refresh_token=None):
        conn = None
        try:
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, mode=0o755, exist_ok=True)
            
            if not os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ItemTable (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')
                conn.commit()
                if sys.platform != "win32":
                    os.chmod(self.db_path, 0o644)
                conn.close()

            conn = sqlite3.connect(self.db_path)
            logging.info('auth.connected.database')
            cursor = conn.cursor()
            
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            
            updates = []
            if email is not None:
                updates.append(("cursorAuth/cachedEmail", email))
            if access_token is not None:
                updates.append(("cursorAuth/accessToken", access_token))
            if refresh_token is not None:
                updates.append(("cursorAuth/refreshToken", refresh_token))
                updates.append(("cursorAuth/cachedSignUpType", "Auth_0"))

            cursor.execute("BEGIN TRANSACTION")
            try:
                for key, value in updates:
                    cursor.execute("SELECT COUNT(*) FROM ItemTable WHERE key = ?", (key,))
                    if cursor.fetchone()[0] == 0:
                        cursor.execute("""
                            INSERT INTO ItemTable (key, value) 
                            VALUES (?, ?)
                        """, (key, value))
                    else:
                        cursor.execute("""
                            UPDATE ItemTable SET value = ?
                            WHERE key = ?
                        """, (value, key))
                    logging.info(f'auth.updating {key.split('/')[-1]}')
                
                cursor.execute("COMMIT")
                logging.info('auth.database.updated.successfully')
                return True
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                raise e

        except sqlite3.Error as e:
            logging.error("database.error:", str(e))
            return False
        except Exception as e:
            logging.error("error:", str(e))
            return False
        finally:
            if conn:
                conn.close()
