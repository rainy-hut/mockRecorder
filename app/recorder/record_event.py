from dataclasses import dataclass

from app.constants import ReplayStrategy


@dataclass
class RecordEvent:
    profile_name: str
    test_item_code: str
    instrument_alias: str
    instrument_type: str
    protocol: str
    payload_format: str
    variant_name: str
    request_text: str
    normalized_request: str
    request_hex: str
    request_hash: str
    request_bytes: bytes
    product_name: str = ""
    process_station: str = ""
    product_code: str = ""
    tu_name: str = ""
    response_text: str = ""
    normalized_response: str = ""
    response_hex: str = ""
    response_hash: str = ""
    response_bytes: bytes = b""
    call_index: int = 1
    replay_strategy: str = ReplayStrategy.BY_CALL_INDEX
    timeout_ms: int = 0
    delay_ms: int = 0
    success: bool = True
    error_type: str = ""
    error_message: str = ""
    source: str = "RECORDED"
    remark: str = ""
