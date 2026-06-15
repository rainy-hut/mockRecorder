import logging
import socket
import time

from app.constants import Mode, PayloadFormat
from app.models import AppConfig, InstrumentConfig
from app.proxy.payload_codec import PayloadCodec
from app.proxy.protocol_codec import is_line_protocol, is_query
from app.proxy.replay_engine import ReplayEngine
from app.recorder.record_event import RecordEvent
from app.recorder.recorder_service import RecorderService
from app.recorder.runtime_context import RuntimeContext

logger = logging.getLogger(__name__)


class TcpProxySession:
    def __init__(
        self,
        client_socket: socket.socket,
        instrument: InstrumentConfig,
        app_config: AppConfig,
        runtime_context: RuntimeContext,
        recorder_service: RecorderService,
        replay_engine: ReplayEngine,
    ):
        self.client_socket = client_socket
        self.instrument = instrument
        self.app_config = app_config
        self.runtime_context = runtime_context
        self.recorder_service = recorder_service
        self.replay_engine = replay_engine

    def run(self) -> None:
        with self.client_socket:
            self.client_socket.settimeout(self.app_config.socketReadTimeoutMs / 1000)
            while True:
                request = self._read_request(self.client_socket)
                if not request:
                    return
                try:
                    self._handle_request(request)
                except Exception:
                    logger.exception("Proxy session failed for %s", self.instrument.alias)
                    return

    def _read_request(self, sock: socket.socket) -> bytes:
        if is_line_protocol(self.instrument.protocol, self.instrument.payloadFormat):
            chunks = []
            while True:
                part = sock.recv(1)
                if not part:
                    break
                chunks.append(part)
                if part == b"\n":
                    break
            return b"".join(chunks)
        return sock.recv(65536)

    def _handle_request(self, request: bytes) -> None:
        request_payload = PayloadCodec.decode(request, self.instrument.payloadFormat)
        context = self.runtime_context.snapshot()
        mode = context["mode"]
        if mode == Mode.REPLAY:
            response = self.replay_engine.replay(self.instrument.alias, request_payload.hash)
            if response:
                self.client_socket.sendall(response)
            return

        start = time.monotonic()
        response = b""
        error_type = ""
        error_message = ""
        success = True
        try:
            response = self._forward_to_real_hardware(request)
            if response:
                self.client_socket.sendall(response)
        except Exception as exc:
            success = False
            error_type = exc.__class__.__name__
            error_message = str(exc)
            logger.exception("Forward failed for %s", self.instrument.alias)
            if mode == Mode.OFF:
                raise
        delay_ms = int((time.monotonic() - start) * 1000)
        if mode == Mode.RECORD:
            response_payload = PayloadCodec.decode(response, self.instrument.payloadFormat) if response else PayloadCodec.decode(b"", PayloadFormat.BINARY)
            call_index = self.runtime_context.next_scene_record_call_index(
                context["product_name"],
                context["process_station"],
                context["product_code"],
                context["tu_name"],
                self.instrument.alias,
                request_payload.hash,
            )
            self.recorder_service.record(RecordEvent(
                product_name=context["product_name"],
                process_station=context["process_station"],
                product_code=context["product_code"],
                tu_name=context["tu_name"],
                profile_name=context["profile_name"],
                test_item_code=context["test_item_code"],
                instrument_alias=self.instrument.alias,
                instrument_type=self.instrument.type,
                protocol=self.instrument.protocol,
                payload_format=self.instrument.payloadFormat,
                variant_name=context["variant_name"],
                request_text=request_payload.text,
                normalized_request=request_payload.normalized,
                request_hex=request_payload.hex,
                request_hash=request_payload.hash,
                request_bytes=request_payload.data,
                response_text=response_payload.text,
                normalized_response=response_payload.normalized,
                response_hex=response_payload.hex,
                response_hash=response_payload.hash,
                response_bytes=response_payload.data,
                call_index=call_index,
                timeout_ms=self.app_config.socketReadTimeoutMs,
                delay_ms=delay_ms,
                success=success,
                error_type=error_type,
                error_message=error_message,
            ))

    def _forward_to_real_hardware(self, request: bytes) -> bytes:
        with socket.create_connection((self.instrument.realHost, self.instrument.realPort), timeout=self.app_config.socketReadTimeoutMs / 1000) as real:
            real.settimeout(self._response_timeout(request) / 1000)
            real.sendall(request)
            try:
                return self._read_response(real)
            except socket.timeout:
                return b""

    def _read_response(self, sock: socket.socket) -> bytes:
        if is_line_protocol(self.instrument.protocol, self.instrument.payloadFormat):
            chunks = []
            while True:
                part = sock.recv(1)
                if not part:
                    break
                chunks.append(part)
                if part == b"\n":
                    break
            return b"".join(chunks)
        return sock.recv(65536)

    def _response_timeout(self, request: bytes) -> int:
        if is_line_protocol(self.instrument.protocol, self.instrument.payloadFormat) and not is_query(request):
            return self.app_config.nonQueryResponseTimeoutMs
        return self.app_config.queryResponseTimeoutMs
