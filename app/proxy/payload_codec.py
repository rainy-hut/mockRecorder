from dataclasses import dataclass

from app.constants import PayloadFormat
from app.proxy.command_normalizer import CommandNormalizer
from app.utils.byte_utils import bytes_to_hex, bytes_to_text, parse_hex_text
from app.utils.hash_utils import sha256_hex


@dataclass
class Payload:
    text: str
    normalized: str
    hex: str
    data: bytes
    hash: str


class PayloadCodec:
    @staticmethod
    def decode(data: bytes, payload_format: str) -> Payload:
        if payload_format == PayloadFormat.TEXT:
            text = bytes_to_text(data)
            normalized = CommandNormalizer.normalize_text(data)
            return Payload(text, normalized, bytes_to_hex(data), data, sha256_hex(normalized.encode("utf-8")))
        if payload_format == PayloadFormat.HEX_TEXT:
            text = bytes_to_text(data).strip()
            parsed = parse_hex_text(text)
            hex_text = bytes_to_hex(parsed)
            return Payload(text, hex_text, hex_text, parsed, sha256_hex(parsed))
        text = bytes_to_text(data)
        hex_text = bytes_to_hex(data)
        return Payload(text, hex_text, hex_text, data, sha256_hex(data))
