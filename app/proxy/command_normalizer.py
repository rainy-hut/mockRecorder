from __future__ import annotations

import re


class CommandNormalizer:
    @staticmethod
    def normalize_text(data: bytes | str) -> str:
        if isinstance(data, bytes):
            text = data.decode("utf-8", errors="replace")
        else:
            text = data
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        text = text.rstrip("\n")
        return re.sub(r"\s+", " ", text)
