from __future__ import annotations

import re


def bytes_to_hex(data: bytes | None) -> str:
    if not data:
        return ""
    return " ".join(f"{byte:02X}" for byte in data)


def parse_hex_text(text: str) -> bytes:
    compact = re.sub(r"\s+", "", text or "")
    if len(compact) % 2:
        raise ValueError("HEX_TEXT length must be even")
    if not re.fullmatch(r"[0-9a-fA-F]*", compact):
        raise ValueError("HEX_TEXT contains non-hex characters")
    return bytes.fromhex(compact)


def bytes_to_text(data: bytes | None) -> str:
    if not data:
        return ""
    return data.decode("utf-8", errors="replace")
