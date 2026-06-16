import socket

from app.constants import Mode, PayloadFormat, ProtocolType
from app.models import AppConfig, InstrumentConfig
from app.proxy.tcp_proxy_session import TcpProxySession
from app.recorder.runtime_context import RuntimeContext


class FakeClientSocket:
    def __init__(self):
        self.sent = b""

    def sendall(self, data: bytes) -> None:
        self.sent += data


class FakeRealSocket:
    def __init__(self, response: bytes):
        self.response = response
        self.sent = b""
        self.closed = False

    def settimeout(self, _timeout: float) -> None:
        pass

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def recv(self, _size: int) -> bytes:
        if not self.response:
            return b""
        part = self.response[:1]
        self.response = self.response[1:]
        return part

    def close(self) -> None:
        self.closed = True


class DummyRecorder:
    def record(self, _event) -> None:
        pass


class DummyReplay:
    pass


def _session(client: FakeClientSocket) -> TcpProxySession:
    instrument = InstrumentConfig(
        alias="SA_TEST",
        protocol=ProtocolType.SOCKET_SCPI_LINE,
        payloadFormat=PayloadFormat.TEXT,
        realHost="127.0.0.1",
        realPort=5025,
    )
    config = AppConfig(mode=Mode.OFF)
    context = RuntimeContext(mode=Mode.OFF)
    return TcpProxySession(client, instrument, config, context, DummyRecorder(), DummyReplay())


def test_off_mode_forwards_request_to_real_hardware_and_response_to_client(monkeypatch):
    client = FakeClientSocket()
    real = FakeRealSocket(b"MOCK,SA,001\n")
    monkeypatch.setattr(socket, "create_connection", lambda *_args, **_kwargs: real)

    session = _session(client)
    session._handle_request(b"*IDN?\n")

    assert real.sent == b"*IDN?\n"
    assert client.sent == b"MOCK,SA,001\n"


def test_query_reconnects_when_reused_real_socket_returns_empty_response(monkeypatch):
    client = FakeClientSocket()
    stale = FakeRealSocket(b"")
    healthy = FakeRealSocket(b"MOCK,SA,001\n")
    connections = iter([stale, healthy])
    monkeypatch.setattr(socket, "create_connection", lambda *_args, **_kwargs: next(connections))

    session = _session(client)
    session._handle_request(b"*IDN?\n")

    assert stale.closed
    assert stale.sent == b"*IDN?\n"
    assert healthy.sent == b"*IDN?\n"
    assert client.sent == b"MOCK,SA,001\n"
