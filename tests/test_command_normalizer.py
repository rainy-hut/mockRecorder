from app.proxy.command_normalizer import CommandNormalizer


def test_normalize_text():
    assert CommandNormalizer.normalize_text(b" READ:ACLR?\r\n") == "READ:ACLR?"
    assert CommandNormalizer.normalize_text("FREQ    3500000000\n") == "FREQ 3500000000"
