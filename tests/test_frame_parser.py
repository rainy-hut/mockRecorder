from app.proxy.frame_parser import StreamFrameParser, build_command_key, command_key_from_bytes


def test_f634_frame_parser_waits_for_complete_frame():
    parser = StreamFrameParser()
    assert parser.feed(b"\xF6\x34\x00\x03A") == []
    frames = parser.feed(b"BC")
    assert len(frames) == 1
    assert frames[0].frame_type == "f634_binary"
    assert frames[0].data == b"\xF6\x34\x00\x03ABC"


def test_parser_handles_multiple_frames_in_one_recv():
    parser = StreamFrameParser()
    frames = parser.feed(b"\xF6\x34\x00\x01A\xF6\x34\x00\x01B")
    assert [frame.data for frame in frames] == [b"\xF6\x34\x00\x01A", b"\xF6\x34\x00\x01B"]


def test_om_response_until_end_marker():
    parser = StreamFrameParser()
    assert parser.feed(b"+++    0\nO&M    #1\n") == []
    frames = parser.feed(b"RETCODE = 0 Operation succeeded.\n---    END\n")
    assert len(frames) == 1
    assert frames[0].frame_type == "om_text"
    assert b"---    END" in frames[0].data


def test_lgi_command_key_ignores_dynamic_fields():
    text = 'LGI: OP="admin", PWD="xxxx", DN=0, AUTHTYPE=PUBLICKEY, RAND="abc", SID=42;'
    assert build_command_key("LGI", text) == "LGI|OP=admin|DN=0|AUTHTYPE=PUBLICKEY"


def test_f634_frame_extracts_inner_lgi_request_command_key():
    payload = (
        b"\x01\xff\xff\x00\x00\x00\x00"
        b'LGI REQUEST: OP="admin", DN=0, TYPE=PUBLICKEY, HASHAL=SHA256, SID=0, RSAPadding=OAEP;'
    )
    frame = b"\xF6\x34" + len(payload).to_bytes(2, "big") + payload
    assert command_key_from_bytes(frame) == "LGI|OP=admin|DN=0|TYPE=PUBLICKEY|HASHAL=SHA256|RSAPADDING=OAEP"


def test_lgi_dynamic_pwd_rand_sid_share_command_key():
    first = b'LGI: OP="admin", PWD="aaa", DN=0, AUTHTYPE=PUBLICKEY, RAND="111", SID=1;'
    second = b'LGI: OP="admin", PWD="bbb", DN=0, AUTHTYPE=PUBLICKEY, RAND="222", SID=2;'
    assert command_key_from_bytes(first) == command_key_from_bytes(second)
