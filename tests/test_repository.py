from app.constants import PayloadFormat, ProtocolType
from app.db.database import Database
from app.db.repository import Repository
from app.recorder.record_event import RecordEvent


def test_insert_and_list_interactions(tmp_path):
    repo = Repository(Database(tmp_path / "recorder.db"))
    repo.init_schema()
    event = RecordEvent(
        profile_name="default",
        test_item_code="ACLR_TEST",
        instrument_alias="SA_01",
        instrument_type="SpectrumAnalyzer",
        protocol=ProtocolType.SOCKET_SCPI_LINE,
        payload_format=PayloadFormat.TEXT,
        variant_name="normal",
        request_text="READ:ACLR?\n",
        normalized_request="READ:ACLR?",
        request_hex="52",
        request_hash="hash1",
        request_bytes=b"READ:ACLR?\n",
        response_text="1.0\n",
        normalized_response="1.0",
        response_hex="31",
        response_hash="hash2",
        response_bytes=b"1.0\n",
    )
    interaction_id = repo.insert_interaction(event)
    assert interaction_id > 0
    assert repo.count_interactions() == 1
    assert repo.list_interactions({"instrument_alias": "SA_01"})[0]["request_hash"] == "hash1"
