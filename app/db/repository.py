from __future__ import annotations

import json
import random
import sqlite3
import base64
from pathlib import Path
from typing import Any

from app.db.database import Database
from app.models import InstrumentConfig
from app.recorder.record_event import RecordEvent
from app.utils.time_utils import utc_now_iso


class Repository:
    def __init__(self, database: Database):
        self.database = database

    def init_schema(self) -> None:
        self.database.init_schema()

    def upsert_profile(self, profile_name: str, description: str | None = None) -> None:
        now = utc_now_iso()
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO record_profile(profile_name, description, created_at, updated_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(profile_name) DO UPDATE SET description=excluded.description, updated_at=excluded.updated_at
                """,
                (profile_name, description, now, now),
            )

    def upsert_test_item(self, test_item_code: str, test_item_name: str | None = None, description: str | None = None) -> None:
        now = utc_now_iso()
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO test_item(test_item_code, test_item_name, description, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(test_item_code) DO UPDATE SET
                    test_item_name=excluded.test_item_name,
                    description=excluded.description,
                    updated_at=excluded.updated_at
                """,
                (test_item_code, test_item_name, description, now, now),
            )

    def save_instrument_config(self, config: InstrumentConfig) -> None:
        now = utc_now_iso()
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO instrument_config(
                    instrument_alias, instrument_type, protocol, payload_format, proxy_host, proxy_port,
                    real_host, real_port, visa_resource, enabled, config_json, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(instrument_alias) DO UPDATE SET
                    instrument_type=excluded.instrument_type, protocol=excluded.protocol,
                    payload_format=excluded.payload_format, proxy_host=excluded.proxy_host,
                    proxy_port=excluded.proxy_port, real_host=excluded.real_host, real_port=excluded.real_port,
                    visa_resource=excluded.visa_resource, enabled=excluded.enabled,
                    config_json=excluded.config_json, updated_at=excluded.updated_at
                """,
                (
                    config.alias, config.type, config.protocol, config.payloadFormat, config.proxyHost,
                    config.proxyPort, config.realHost, config.realPort, config.visaResource,
                    int(config.enabled), json.dumps(config.to_dict(), ensure_ascii=False), now, now,
                ),
            )

    def create_tcp_session(
        self,
        session_id: str,
        instrument_alias: str,
        client_host: str,
        client_port: int,
        proxy_host: str,
        proxy_port: int,
        real_host: str,
        real_port: int,
    ) -> None:
        now = utc_now_iso()
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tcp_session(
                    session_id, instrument_alias, client_host, client_port,
                    proxy_host, proxy_port, real_host, real_port, started_at, ended_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (session_id, instrument_alias, client_host, client_port, proxy_host, proxy_port, real_host, real_port, now),
            )

    def finish_tcp_session(self, session_id: str) -> None:
        with self.database.connect() as conn:
            conn.execute("UPDATE tcp_session SET ended_at=? WHERE session_id=?", (utc_now_iso(), session_id))

    def insert_interaction(self, event: RecordEvent) -> int:
        now = utc_now_iso()
        with self.database.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO interaction_record(
                    product_name, process_station, product_code, tu_name,
                    profile_name, test_item_code, instrument_alias, instrument_type, protocol, payload_format,
                    variant_name, replay_strategy, request_text, normalized_request, request_hex, request_hash,
                    response_text, normalized_response, response_hex, response_hash, request_bytes, response_bytes,
                    call_index, timeout_ms, delay_ms, success, error_type, error_message, source, remark, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.product_name, event.process_station, event.product_code, event.tu_name,
                    event.profile_name, event.test_item_code, event.instrument_alias, event.instrument_type,
                    event.protocol, event.payload_format, event.variant_name, event.replay_strategy,
                    event.request_text, event.normalized_request, event.request_hex, event.request_hash,
                    event.response_text, event.normalized_response, event.response_hex, event.response_hash,
                    event.request_bytes, event.response_bytes, event.call_index, event.timeout_ms,
                    event.delay_ms, int(event.success), event.error_type, event.error_message,
                    event.source, event.remark, now, now,
                ),
            )
            interaction_id = int(cur.lastrowid)
            self.insert_stream_frame_dict(conn, interaction_id, event, "TX", event.request_text, event.request_hex, event.request_bytes)
            if event.response_bytes or event.response_text:
                self.insert_stream_frame_dict(conn, interaction_id, event, "RX", event.response_text, event.response_hex, event.response_bytes)
            return interaction_id

    def insert_stream_frame_dict(self, conn: sqlite3.Connection, interaction_id: int, event: RecordEvent, direction: str, text: str, hex_text: str, data: bytes) -> None:
        conn.execute(
            """
            INSERT INTO stream_frame(
                interaction_id, product_name, process_station, product_code, tu_name,
                profile_name, test_item_code, instrument_alias, direction, protocol, payload_format,
                data_text, data_hex, raw_hex, raw_base64, text_preview,
                data_blob, data_length, timestamp
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction_id, event.product_name, event.process_station, event.product_code, event.tu_name,
                event.profile_name, event.test_item_code, event.instrument_alias, direction,
                event.protocol, event.payload_format, text, hex_text, hex_text,
                base64.b64encode(data or b"").decode("ascii"), text, data, len(data or b""), utc_now_iso(),
            ),
        )

    def insert_raw_stream_frame(
        self,
        *,
        session_id: str,
        seq_no: int,
        instrument_alias: str,
        direction: str,
        protocol: str,
        payload_format: str,
        data: bytes,
        product_name: str = "",
        process_station: str = "",
        product_code: str = "",
        tu_name: str = "",
        profile_name: str = "",
        test_item_code: str = "",
        peer_host: str = "",
        peer_port: int = 0,
        frame_type: str = "raw_recv",
        parsed_command: str = "",
        command_key: str = "",
        text_preview: str = "",
        delay_ms_from_prev: int = 0,
    ) -> None:
        hex_text = " ".join(f"{byte:02X}" for byte in data)
        preview = text_preview if text_preview else self._text_preview(data)
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO stream_frame(
                    session_id, seq_no, product_name, process_station, product_code, tu_name,
                    profile_name, test_item_code, instrument_alias, direction, protocol, payload_format,
                    data_text, data_hex, raw_hex, raw_base64, text_preview, frame_type,
                    parsed_command, command_key, peer_host, peer_port, delay_ms_from_prev,
                    data_blob, data_length, timestamp
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, seq_no, product_name, process_station, product_code, tu_name,
                    profile_name, test_item_code, instrument_alias, direction, protocol, payload_format,
                    preview, hex_text, hex_text, base64.b64encode(data).decode("ascii"), preview,
                    frame_type, parsed_command, command_key, peer_host, peer_port, delay_ms_from_prev,
                    data, len(data), utc_now_iso(),
                ),
            )

    def list_stream_frames(self, session_id: str | None = None) -> list[sqlite3.Row]:
        with self.database.connect() as conn:
            if session_id:
                return list(conn.execute("SELECT * FROM stream_frame WHERE session_id=? ORDER BY seq_no ASC, id ASC", (session_id,)))
            return list(conn.execute("SELECT * FROM stream_frame ORDER BY id ASC"))

    def _text_preview(self, data: bytes) -> str:
        for encoding in ("utf-8", "gbk", "latin1"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    def insert_stream_frame(self, frame: dict[str, Any]) -> None:
        keys = ", ".join(frame.keys())
        placeholders = ", ".join("?" for _ in frame)
        with self.database.connect() as conn:
            conn.execute(f"INSERT INTO stream_frame({keys}) VALUES({placeholders})", tuple(frame.values()))

    def find_replay_records(
        self,
        profile_name: str,
        test_item_code: str,
        instrument_alias: str,
        request_hash: str,
        variant_name: str = "normal",
        call_index: int = 1,
        strategy: str = "BY_CALL_INDEX",
        product_name: str = "",
        process_station: str = "",
        product_code: str = "",
        tu_name: str = "",
    ) -> list[sqlite3.Row]:
        cases = [
            ("product_name=? AND process_station=? AND product_code=? AND tu_name=? AND instrument_alias=? AND request_hash=? AND call_index=?", (product_name, process_station, product_code, tu_name, instrument_alias, request_hash, call_index)),
            ("product_name=? AND process_station=? AND product_code=? AND tu_name=? AND instrument_alias=? AND request_hash=?", (product_name, process_station, product_code, tu_name, instrument_alias, request_hash)),
            ("product_name=? AND process_station=? AND product_code=? AND instrument_alias=? AND request_hash=?", (product_name, process_station, product_code, instrument_alias, request_hash)),
            ("profile_name=? AND test_item_code=? AND instrument_alias=? AND request_hash=? AND variant_name=? AND call_index=?", (profile_name, test_item_code, instrument_alias, request_hash, variant_name, call_index)),
            ("profile_name=? AND test_item_code=? AND instrument_alias=? AND request_hash=? AND call_index=?", (profile_name, test_item_code, instrument_alias, request_hash, call_index)),
            ("profile_name=? AND test_item_code=? AND instrument_alias=? AND request_hash=?", (profile_name, test_item_code, instrument_alias, request_hash)),
            ("profile_name=? AND instrument_alias=? AND request_hash=?", (profile_name, instrument_alias, request_hash)),
            ("profile_name=? AND instrument_alias=? AND request_hash=?", ("default", instrument_alias, request_hash)),
        ]
        with self.database.connect() as conn:
            for where, params in cases:
                rows = list(conn.execute(f"SELECT * FROM interaction_record WHERE {where} ORDER BY call_index ASC, id ASC", params))
                if rows:
                    if strategy == "FIRST":
                        return [rows[0]]
                    if strategy == "LAST":
                        return [rows[-1]]
                    if strategy == "RANDOM":
                        return [random.choice(rows)]
                    return rows
        return []

    def count_interactions(self, filters: dict[str, Any] | None = None) -> int:
        where, params = self._build_filters(filters)
        with self.database.connect() as conn:
            row = conn.execute(f"SELECT COUNT(*) AS n FROM interaction_record {where}", params).fetchone()
            return int(row["n"])

    def list_interactions(self, filters: dict[str, Any] | None = None, limit: int = 500, offset: int = 0) -> list[sqlite3.Row]:
        where, params = self._build_filters(filters)
        with self.database.connect() as conn:
            return list(conn.execute(
                f"SELECT * FROM interaction_record {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ))

    def delete_interaction(self, interaction_id: int) -> None:
        with self.database.connect() as conn:
            conn.execute("DELETE FROM stream_frame WHERE interaction_id=?", (interaction_id,))
            conn.execute("DELETE FROM interaction_record WHERE id=?", (interaction_id,))

    def update_interaction(self, interaction_id: int, fields: dict[str, Any]) -> None:
        allowed = {
            "product_name", "process_station", "product_code", "tu_name", "instrument_alias",
            "protocol", "payload_format", "request_text", "normalized_request", "request_hex",
            "request_hash", "response_text", "normalized_response", "response_hex",
            "response_hash", "call_index", "replay_strategy", "success", "remark",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        updates["updated_at"] = utc_now_iso()
        assignments = ", ".join(f"{key}=?" for key in updates)
        with self.database.connect() as conn:
            conn.execute(
                f"UPDATE interaction_record SET {assignments} WHERE id=?",
                [*updates.values(), interaction_id],
            )

    def insert_interaction_dict(self, data: dict[str, Any]) -> int:
        now = utc_now_iso()
        allowed = [
            "product_name", "process_station", "product_code", "tu_name",
            "profile_name", "test_item_code", "instrument_alias", "instrument_type",
            "protocol", "payload_format", "variant_name", "replay_strategy",
            "request_text", "normalized_request", "request_hex", "request_hash",
            "response_text", "normalized_response", "response_hex", "response_hash",
            "call_index", "timeout_ms", "delay_ms", "success", "error_type",
            "error_message", "source", "remark",
        ]
        row = {key: data.get(key) for key in allowed}
        row["profile_name"] = row.get("profile_name") or "default"
        row["test_item_code"] = row.get("test_item_code") or "DEFAULT_TEST"
        row["variant_name"] = row.get("variant_name") or "normal"
        row["source"] = row.get("source") or "IMPORTED"
        row["created_at"] = data.get("created_at") or now
        row["updated_at"] = now
        keys = list(row.keys())
        placeholders = ", ".join("?" for _ in keys)
        with self.database.connect() as conn:
            cur = conn.execute(
                f"INSERT INTO interaction_record({', '.join(keys)}) VALUES({placeholders})",
                [row[key] for key in keys],
            )
            return int(cur.lastrowid)

    def export_interactions_to_json(self, filters: dict[str, Any], output_path: str | Path) -> None:
        rows = [dict(row) for row in self.list_interactions(filters, limit=100000)]
        for row in rows:
            row["request_bytes"] = row["request_hex"]
            row["response_bytes"] = row["response_hex"]
        Path(output_path).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def import_interactions_from_json(self, input_path: str | Path) -> int:
        raw = json.loads(Path(input_path).read_text(encoding="utf-8"))
        rows = raw if isinstance(raw, list) else raw.get("records", [])
        count = 0
        for row in rows:
            if isinstance(row, dict):
                row.pop("id", None)
                self.insert_interaction_dict(row)
                count += 1
        return count

    def execute_sql(self, sql: str) -> tuple[list[str], list[tuple[Any, ...]], int]:
        statement = sql.strip()
        if not statement:
            return [], [], 0
        with self.database.connect() as conn:
            if statement.lower().startswith(("select", "pragma")):
                cur = conn.execute(statement)
                columns = [item[0] for item in cur.description or []]
                rows = [tuple(row) for row in cur.fetchall()]
                return columns, rows, len(rows)
            cur = conn.execute(statement)
            return [], [], cur.rowcount

    def _build_filters(self, filters: dict[str, Any] | None) -> tuple[str, list[Any]]:
        if not filters:
            return "", []
        clauses = []
        params: list[Any] = []
        for key in ["product_name", "process_station", "product_code", "tu_name", "profile_name", "test_item_code", "instrument_alias", "protocol", "payload_format", "variant_name", "request_hash"]:
            value = filters.get(key)
            if value:
                clauses.append(f"{key}=?")
                params.append(value)
        for key in ["request_text", "request_hex"]:
            value = filters.get(key)
            if value:
                clauses.append(f"{key} LIKE ?")
                params.append(f"%{value}%")
        if filters.get("success") in (0, 1, "0", "1"):
            clauses.append("success=?")
            params.append(int(filters["success"]))
        if filters.get("created_from"):
            clauses.append("created_at>=?")
            params.append(filters["created_from"])
        if filters.get("created_to"):
            clauses.append("created_at<=?")
            params.append(filters["created_to"])
        return ("WHERE " + " AND ".join(clauses), params) if clauses else ("", [])
