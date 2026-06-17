from __future__ import annotations

import logging

from app.constants import ReplayStrategy
from app.db.repository import Repository
from app.proxy.frame_parser import command_key_from_bytes
from app.recorder.runtime_context import RuntimeContext

logger = logging.getLogger(__name__)


class ReplayEngine:
    def __init__(self, repository: Repository, runtime_context: RuntimeContext, append_new_line: bool = True):
        self.repository = repository
        self.runtime_context = runtime_context
        self.append_new_line = append_new_line

    def replay(self, instrument_alias: str, request_hash: str, strategy: str = ReplayStrategy.BY_CALL_INDEX, request_bytes: bytes = b"") -> bytes:
        context = self.runtime_context.snapshot()
        if request_bytes:
            command_key = command_key_from_bytes(request_bytes)
            if command_key:
                stream_rows = self.repository.find_response_frames_by_command_key(
                    instrument_alias,
                    command_key,
                    product_name=context["product_name"],
                    process_station=context["process_station"],
                    product_code=context["product_code"],
                    tu_name=context["tu_name"],
                )
                if stream_rows:
                    logger.debug("Replay stream hit instrument=%s command_key=%s frames=%s", instrument_alias, command_key, len(stream_rows))
                    return b"".join(row["data_blob"] or b"" for row in stream_rows)
        call_index = self.runtime_context.next_scene_replay_call_index(
            context["product_name"],
            context["process_station"],
            context["product_code"],
            context["tu_name"],
            instrument_alias,
            request_hash,
        )
        rows = self.repository.find_replay_records(
            context["profile_name"],
            context["test_item_code"],
            instrument_alias,
            request_hash,
            context["variant_name"],
            call_index,
            strategy,
            product_name=context["product_name"],
            process_station=context["process_station"],
            product_code=context["product_code"],
            tu_name=context["tu_name"],
        )
        if not rows:
            logger.debug("Replay miss instrument=%s hash=%s call=%s", instrument_alias, request_hash, call_index)
            return b""
        if strategy == ReplayStrategy.BY_CALL_INDEX and len(rows) > 1:
            response = b"".join(self._row_response(row) for row in rows)
            logger.debug("Replay multi-hit instrument=%s hash=%s call=%s records=%s", instrument_alias, request_hash, call_index, len(rows))
            return response
        row = self._select_row(rows, strategy, context, instrument_alias, request_hash)
        response = self._row_response(row)
        if self.append_new_line and row["response_bytes"] is None and row["payload_format"] == "TEXT" and response and not response.endswith((b"\n", b"\r\n")):
            response += b"\n"
        logger.debug("Replay hit instrument=%s hash=%s call=%s record=%s", instrument_alias, request_hash, call_index, row["id"])
        return response

    def _row_response(self, row) -> bytes:
        response = row["response_bytes"] if row["response_bytes"] is not None else (row["response_text"] or "").encode("utf-8")
        return response

    def _select_row(self, rows, strategy: str, context: dict[str, str], instrument_alias: str, request_hash: str):
        if strategy == ReplayStrategy.ROUND_ROBIN:
            idx = self.runtime_context.next_scene_round_robin_index(
                context["product_name"],
                context["process_station"],
                context["product_code"],
                context["tu_name"],
                instrument_alias,
                request_hash,
            )
            return rows[(idx - 1) % len(rows)]
        if strategy == ReplayStrategy.LAST:
            return rows[-1]
        return rows[0]
