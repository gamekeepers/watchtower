import sqlite3
import os

# default path home folder
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", f"{os.path.expanduser('~')}/watchtower/watchtower.db")


def setup_sqlite_db():
    if not SQLITE_DB_PATH:
        raise ValueError(
            "Please provide SQLITE_DB_PATH"
        )

    directory = os.path.dirname(SQLITE_DB_PATH)
    if not os.path.exists(directory):
        os.makedirs(directory)

    sqlite_client = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_client.execute(
        "CREATE TABLE IF NOT EXISTS literatures (md5_hash TEXT PRIMARY KEY, title TEXT, content TEXT)")


def get_connection():
    return sqlite3.connect(SQLITE_DB_PATH)
