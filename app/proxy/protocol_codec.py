from app.constants import ProtocolType


def is_line_protocol(protocol: str, payload_format: str) -> bool:
    return protocol in (ProtocolType.SOCKET_SCPI_LINE, ProtocolType.VISA_SOCKET) and payload_format == "TEXT"


def is_query(request: bytes) -> bool:
    return b"?" in request
