from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParsedFrame:
    data: bytes
    frame_type: str
    parsed_command: str = ""
    command_key: str = ""
    text_preview: str = ""


class StreamFrameParser:
    def __init__(self):
        self.buffer = b""

    def feed(self, data: bytes) -> list[ParsedFrame]:
        self.buffer += data
        frames: list[ParsedFrame] = []
        while self.buffer:
            frame = self._next_frame()
            if frame is None:
                break
            frames.append(frame)
        return frames

    def flush_raw(self) -> ParsedFrame | None:
        if not self.buffer:
            return None
        data = self.buffer
        self.buffer = b""
        return self._parsed(data, "raw")

    def _next_frame(self) -> ParsedFrame | None:
        if self.buffer.startswith(b"\xF6\x34"):
            if len(self.buffer) < 4:
                return None
            body_len = int.from_bytes(self.buffer[2:4], "big")
            frame_len = 4 + body_len
            if len(self.buffer) < frame_len:
                return None
            data = self._consume(frame_len)
            return self._parsed(data, "f634_binary")

        end_marker = b"---    END"
        end_index = self.buffer.find(end_marker)
        if self._looks_like_om_text(self.buffer):
            if end_index == -1:
                return None
            line_end = self._line_end_after(end_index + len(end_marker))
            if line_end is None:
                return None
            data = self._consume(line_end)
            return self._parsed(data, "om_text")

        semicolon = self.buffer.find(b";")
        newline = self._first_newline(self.buffer)
        candidates = [idx for idx in (semicolon, newline) if idx != -1]
        if candidates and self._looks_textual(self.buffer[: min(candidates) + 1]):
            end = min(candidates) + 1
            data = self._consume(end)
            return self._parsed(data, "text")
        return None

    def _consume(self, length: int) -> bytes:
        data = self.buffer[:length]
        self.buffer = self.buffer[length:]
        return data

    def _line_end_after(self, start: int) -> int | None:
        for marker in (b"\r\n", b"\n"):
            idx = self.buffer.find(marker, start)
            if idx != -1:
                return idx + len(marker)
        return len(self.buffer) if start <= len(self.buffer) else None

    def _first_newline(self, data: bytes) -> int:
        indexes = [idx for idx in (data.find(b"\r\n"), data.find(b"\n")) if idx != -1]
        return min(indexes) if indexes else -1

    def _looks_like_om_text(self, data: bytes) -> bool:
        preview = self._decode_preview(data[:512])
        return "+++" in preview or "O&M" in preview or "%%" in preview

    def _looks_textual(self, data: bytes) -> bool:
        if not data:
            return False
        control = sum(1 for byte in data if byte < 32 and byte not in (9, 10, 13))
        return control == 0

    def _parsed(self, data: bytes, frame_type: str) -> ParsedFrame:
        preview = self._decode_preview(self._semantic_payload(data, frame_type))
        command = extract_command(preview)
        return ParsedFrame(data, frame_type, command, build_command_key(command, preview), preview)

    def _semantic_payload(self, data: bytes, frame_type: str) -> bytes:
        if frame_type != "f634_binary":
            return data
        payload = data[4:]
        markers = [idx for idx in (payload.find(b"+++"), payload.find(b"%%")) if idx != -1]
        if markers:
            return payload[min(markers):]
        for index, byte in enumerate(payload):
            if 32 <= byte <= 126:
                return payload[index:]
        return payload

    def _decode_preview(self, data: bytes) -> str:
        for encoding in ("utf-8", "gbk", "latin1"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")


def extract_command(text: str) -> str:
    cleaned = text.strip()
    match = re.search(r"%%\s*([A-Z][A-Z0-9_ ]+?)(?::|\s+REQUEST|\s*;)", cleaned, re.I)
    if not match:
        match = re.search(r"\b([A-Z][A-Z0-9_ ]+?)(?::|\s+REQUEST|\s*;)", cleaned, re.I)
    return " ".join(match.group(1).upper().split()) if match else ""


def build_command_key(command: str, text: str) -> str:
    if not command:
        return ""
    ignored = {
        "PWD", "RAND", "SID", "SESSIONID", "SESSION_ID", "HASH", "PUBLICKEY", "TIMESTAMP", "TIME",
        "RETCODE", "ACK", "KEY", "IP",
    }
    parts = [command]
    for key, value in re.findall(r"\b([A-Z][A-Z0-9_]*)\s*=\s*\"?([^\",\s;]+)", text, flags=re.I):
        key_upper = key.upper()
        if key_upper in ignored:
            continue
        parts.append(f"{key_upper}={value}")
    return "|".join(parts)


def command_key_from_bytes(data: bytes) -> str:
    parser = StreamFrameParser()
    frames = parser.feed(data)
    if not frames:
        frame = parser.flush_raw()
        frames = [frame] if frame else []
    for frame in frames:
        if frame.command_key:
            return frame.command_key
    return ""
