from app.constants import PayloadFormat, ProtocolType
from app.db.database import Database
from app.db.repository import Repository
from app.proxy.replay_engine import ReplayEngine
from app.recorder.record_event import RecordEvent
from app.recorder.runtime_context import RuntimeContext


def test_replay_by_hash_and_call_index(tmp_path):
    repo = Repository(Database(tmp_path / "recorder.db"))
    repo.init_schema()
    for idx, response in [(1, b"first\n"), (2, b"second\n")]:
        repo.insert_interaction(RecordEvent(
            profile_name="default",
            test_item_code="DEFAULT_TEST",
            instrument_alias="SA_01",
            instrument_type="SpectrumAnalyzer",
            protocol=ProtocolType.SOCKET_SCPI_LINE,
            payload_format=PayloadFormat.TEXT,
            variant_name="normal",
            request_text="READ?\n",
            normalized_request="READ?",
            request_hex="",
            request_hash="hash-read",
            request_bytes=b"READ?\n",
            response_text=response.decode(),
            normalized_response=response.decode().strip(),
            response_hex="",
            response_hash="",
            response_bytes=response,
            call_index=idx,
        ))
    ctx = RuntimeContext(profile_name="default", test_item_code="DEFAULT_TEST")
    engine = ReplayEngine(repo, ctx)
    assert engine.replay("SA_01", "hash-read") == b"first\n"
    assert engine.replay("SA_01", "hash-read") == b"second\n"


def test_replay_prefers_product_station_code_and_tu_name(tmp_path):
    repo = Repository(Database(tmp_path / "recorder.db"))
    repo.init_schema()
    for tu_name, response in [("测试项A", b"A\n"), ("测试项B", b"B\n")]:
        repo.insert_interaction(RecordEvent(
            product_name="MM",
            process_station="FT1-MP1",
            product_code="03020001",
            tu_name=tu_name,
            profile_name="default",
            test_item_code="DEFAULT_TEST",
            instrument_alias="SA_01",
            instrument_type="SpectrumAnalyzer",
            protocol=ProtocolType.SOCKET_SCPI_LINE,
            payload_format=PayloadFormat.TEXT,
            variant_name="normal",
            request_text="READ?\n",
            normalized_request="READ?",
            request_hex="",
            request_hash="hash-read",
            request_bytes=b"READ?\n",
            response_text=response.decode(),
            normalized_response=response.decode().strip(),
            response_hex="",
            response_hash="",
            response_bytes=response,
            call_index=1,
        ))
    ctx = RuntimeContext(
        profile_name="default",
        test_item_code="DEFAULT_TEST",
        product_name="MM",
        process_station="FT1-MP1",
        product_code="03020001",
        tu_name="测试项B",
    )
    engine = ReplayEngine(repo, ctx)
    assert engine.replay("SA_01", "hash-read") == b"B\n"


def test_replay_sends_raw_bytes_without_appending_newline(tmp_path):
    repo = Repository(Database(tmp_path / "recorder.db"))
    repo.init_schema()
    repo.insert_interaction(RecordEvent(
        profile_name="default",
        test_item_code="DEFAULT_TEST",
        instrument_alias="SA_01",
        instrument_type="SpectrumAnalyzer",
        protocol=ProtocolType.SOCKET_SCPI_LINE,
        payload_format=PayloadFormat.TEXT,
        variant_name="normal",
        request_text="READ?\n",
        normalized_request="READ?",
        request_hex="",
        request_hash="hash-read",
        request_bytes=b"READ?\n",
        response_text="OK",
        response_bytes=b"OK",
        call_index=1,
    ))
    engine = ReplayEngine(repo, RuntimeContext(profile_name="default", test_item_code="DEFAULT_TEST"))
    assert engine.replay("SA_01", "hash-read") == b"OK"


def test_replay_returns_multiple_responses_for_same_request_in_order(tmp_path):
    repo = Repository(Database(tmp_path / "recorder.db"))
    repo.init_schema()
    for response in [b"ACK", b"BUSINESS"]:
        repo.insert_interaction(RecordEvent(
            profile_name="default",
            test_item_code="DEFAULT_TEST",
            instrument_alias="SA_01",
            instrument_type="SpectrumAnalyzer",
            protocol=ProtocolType.SOCKET_RAW,
            payload_format=PayloadFormat.BINARY,
            variant_name="normal",
            request_text="",
            normalized_request="01",
            request_hex="01",
            request_hash="hash-bin",
            request_bytes=b"\x01",
            response_bytes=response,
            call_index=1,
        ))
    engine = ReplayEngine(repo, RuntimeContext(profile_name="default", test_item_code="DEFAULT_TEST"))
    assert engine.replay("SA_01", "hash-bin") == b"ACKBUSINESS"


def test_replay_matches_stream_frames_by_command_key_and_returns_multiple_raw_responses(tmp_path):
    repo = Repository(Database(tmp_path / "recorder.db"))
    repo.init_schema()
    request = b'LGI: OP="admin", PWD="recorded", DN=0, AUTHTYPE=PUBLICKEY, RAND="111", SID=1;'
    replay_request = b'LGI: OP="admin", PWD="new", DN=0, AUTHTYPE=PUBLICKEY, RAND="222", SID=2;'
    command_key = "LGI|OP=admin|DN=0|AUTHTYPE=PUBLICKEY"
    for seq, direction, data, frame_type, key in [
        (1, "TX", request, "text", command_key),
        (2, "RX", b"\r\n", "raw_recv", ""),
        (3, "RX", "+++ 0\r\nRETCODE = 0  执行成功\r\n---    END\r\n".encode("gbk"), "raw_recv", ""),
    ]:
        repo.insert_raw_stream_frame(
            session_id="session-1",
            seq_no=seq,
            instrument_alias="SA_01",
            direction=direction,
            protocol=ProtocolType.SOCKET_RAW,
            payload_format=PayloadFormat.BINARY,
            data=data,
            frame_type=frame_type,
            command_key=key,
        )
    engine = ReplayEngine(repo, RuntimeContext(profile_name="default", test_item_code="DEFAULT_TEST"))
    response = engine.replay("SA_01", "unused", request_bytes=replay_request)
    assert response == b"\r\n" + "+++ 0\r\nRETCODE = 0  执行成功\r\n---    END\r\n".encode("gbk")
