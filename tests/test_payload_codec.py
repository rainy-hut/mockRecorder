from app.constants import PayloadFormat
from app.proxy.payload_codec import PayloadCodec


def test_text_hash_uses_normalized_text():
    a = PayloadCodec.decode(b" READ:ACLR?\r\n", PayloadFormat.TEXT)
    b = PayloadCodec.decode(b"READ:ACLR?", PayloadFormat.TEXT)
    assert a.hash == b.hash


def test_hex_text_normalizes_to_bytes():
    a = PayloadCodec.decode(b"01 03 00 00 00 02 C4 0B", PayloadFormat.HEX_TEXT)
    b = PayloadCodec.decode(b"010300000002C40B", PayloadFormat.HEX_TEXT)
    assert a.data == b.data
    assert a.hex == "01 03 00 00 00 02 C4 0B"
    assert a.hash == b.hash
