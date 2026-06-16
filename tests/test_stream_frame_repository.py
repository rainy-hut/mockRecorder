from app.constants import PayloadFormat, ProtocolType
from app.db.database import Database
from app.db.repository import Repository


def test_records_raw_stream_frame_with_session_metadata(tmp_path):
    repo = Repository(Database(tmp_path / "recorder.db"))
    repo.init_schema()
    repo.create_tcp_session(
        "session-1",
        "SA_01",
        "127.0.0.1",
        50000,
        "127.0.0.1",
        15026,
        "192.168.1.20",
        5025,
    )
    repo.insert_raw_stream_frame(
        session_id="session-1",
        seq_no=1,
        instrument_alias="SA_01",
        direction="RX",
        protocol=ProtocolType.SOCKET_RAW,
        payload_format=PayloadFormat.BINARY,
        data="成功".encode("gbk"),
        peer_host="192.168.1.20",
        peer_port=5025,
        frame_type="raw_recv",
    )

    frame = repo.list_stream_frames("session-1")[0]
    assert frame["session_id"] == "session-1"
    assert frame["direction"] == "RX"
    assert frame["raw_base64"]
    assert frame["data_blob"] == "成功".encode("gbk")
    assert "成功" in frame["text_preview"]
