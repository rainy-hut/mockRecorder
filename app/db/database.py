import sqlite3
from pathlib import Path

from app.paths import resource_path


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self) -> None:
        schema_path = resource_path("app/db/schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        index_start = schema.find("CREATE INDEX")
        table_schema = schema if index_start == -1 else schema[:index_start]
        index_schema = "" if index_start == -1 else schema[index_start:]
        with self.connect() as conn:
            conn.executescript(table_schema)
            self._ensure_columns(conn)
            if index_schema:
                conn.executescript(index_schema)

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        required = {
            "tcp_session": {
                "session_id": "TEXT",
                "instrument_alias": "TEXT",
                "client_host": "TEXT",
                "client_port": "INTEGER",
                "proxy_host": "TEXT",
                "proxy_port": "INTEGER",
                "real_host": "TEXT",
                "real_port": "INTEGER",
                "started_at": "TEXT",
                "ended_at": "TEXT",
            },
            "interaction_record": {
                "product_name": "TEXT",
                "process_station": "TEXT",
                "product_code": "TEXT",
                "tu_name": "TEXT",
            },
            "stream_frame": {
                "session_id": "TEXT",
                "seq_no": "INTEGER",
                "product_name": "TEXT",
                "process_station": "TEXT",
                "product_code": "TEXT",
                "tu_name": "TEXT",
                "raw_hex": "TEXT",
                "raw_base64": "TEXT",
                "text_preview": "TEXT",
                "frame_type": "TEXT",
                "parsed_command": "TEXT",
                "command_key": "TEXT",
                "peer_host": "TEXT",
                "peer_port": "INTEGER",
                "delay_ms_from_prev": "INTEGER DEFAULT 0",
            },
        }
        for table, columns in required.items():
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            for name, column_type in columns.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")
