from pathlib import Path
import sqlite3

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT_DIR / "data" / "supplier_scoring.db"
DEFAULT_SCHEMA_PATH = ROOT_DIR / "data" / "schema.sql"

def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys enabled."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def initialize_database(db_path: str | Path = DEFAULT_DB_PATH, schema_path: str | Path = DEFAULT_SCHEMA_PATH) -> None:
    """Initialize the SQLite database by executing the schema script."""
    schema_path = Path(schema_path)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")

    conn = get_connection(db_path)
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    initialize_database()
    print(f"Database initialized successfully at {DEFAULT_DB_PATH}.")
