import logging
import socket
import threading
import time
import uuid

from app.constants import Mode, PayloadFormat
from app.models import AppConfig, InstrumentConfig
from app.db.repository import Repository
from app.proxy.frame_parser import StreamFrameParser
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
        self.real_socket: socket.socket | None = None
        self.repository: Repository | None = getattr(getattr(recorder_service, "writer", None), "repository", None)
        self.session_id = f"{instrument.alias}-{uuid.uuid4().hex}"
        self._seq_no = 0
        self._seq_lock = threading.Lock()
        self._record_lock = threading.Lock()
        self._last_request_payload = None
        self._last_request_context = None
        self._last_request_call_index = 0

    def run(self) -> None:
        if self.runtime_context.snapshot()["mode"] != Mode.REPLAY:
            self._run_transparent_proxy()
            return
        self._run_replay_loop()

    def _run_replay_loop(self) -> None:
        try:
            with self.client_socket:
                self.client_socket.settimeout(self.app_config.socketReadTimeoutMs / 1000)
                while True:
                    try:
                        request = self._read_request(self.client_socket)
                    except socket.timeout:
                        continue
                    if not request:
                        return
                    try:
                        self._handle_request(request)
                    except Exception:
                        logger.exception("Proxy session failed for %s", self.instrument.alias)
                        return
        finally:
            self._close_real_socket()

    def _run_transparent_proxy(self) -> None:
        try:
            with self.client_socket:
                self.real_socket = self._get_real_socket()
                self._create_session_record()
                client_to_real = threading.Thread(
                    target=self._relay,
                    args=(self.client_socket, self.real_socket, "TX"),
                    name=f"Relay-TX-{self.instrument.alias}",
                    daemon=True,
                )
                real_to_client = threading.Thread(
                    target=self._relay,
                    args=(self.real_socket, self.client_socket, "RX"),
                    name=f"Relay-RX-{self.instrument.alias}",
                    daemon=True,
                )
                client_to_real.start()
                real_to_client.start()
                while client_to_real.is_alive() and real_to_client.is_alive():
                    time.sleep(0.05)
        except Exception:
            logger.exception("Transparent proxy failed for %s", self.instrument.alias)
        finally:
            self._finish_session_record()
            self._close_real_socket()

    def _relay(self, source: socket.socket, target: socket.socket, direction: str) -> None:
        parser = StreamFrameParser()
        last_recv_at = time.monotonic()
        source.settimeout(0.5)
        while True:
            try:
                data = source.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                return
            if not data:
                return
            now = time.monotonic()
            delay_ms = int((now - last_recv_at) * 1000)
            last_recv_at = now
            try:
                target.sendall(data)
            except OSError:
                return
            self._record_recv_frame(direction, data, delay_ms, "raw_recv")
            for frame in parser.feed(data):
                self._record_recv_frame(
                    direction,
                    frame.data,
                    0,
                    frame.frame_type,
                    frame.parsed_command,
                    frame.command_key,
                    frame.text_preview,
                )
            if direction == "TX":
                self._remember_request(data)
            elif self.runtime_context.snapshot()["mode"] == Mode.RECORD:
                self._record_compat_interaction(data)

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
            self._log_raw_stream("TX", request)
            response = self.replay_engine.replay(self.instrument.alias, request_payload.hash, request_bytes=request)
            if response:
                self._log_raw_stream("RX", response)
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
        try:
            response = self._send_and_receive(request)
        except OSError:
            self._close_real_socket()
            return self._send_and_receive(request)
        if not response and is_query(request):
            self._close_real_socket()
            return self._send_and_receive(request)
        return response

    def _send_and_receive(self, request: bytes) -> bytes:
        real = self._get_real_socket()
        real.settimeout(self._response_timeout(request) / 1000)
        real.sendall(request)
        try:
            return self._read_response(real)
        except socket.timeout:
            return b""

    def _get_real_socket(self) -> socket.socket:
        if self.real_socket is None:
            self.real_socket = socket.create_connection(
                (self.instrument.realHost, self.instrument.realPort),
                timeout=self.app_config.socketReadTimeoutMs / 1000,
            )
            logger.debug(
                "Connected real instrument %s %s:%s",
                self.instrument.alias,
                self.instrument.realHost,
                self.instrument.realPort,
            )
        return self.real_socket

    def _close_real_socket(self) -> None:
        if self.real_socket is None:
            return
        try:
            self.real_socket.close()
        except OSError:
            pass
        finally:
            self.real_socket = None

    def _create_session_record(self) -> None:
        if not self.repository:
            return
        try:
            client_host, client_port = self.client_socket.getpeername()
        except OSError:
            client_host, client_port = "", 0
        self.repository.create_tcp_session(
            self.session_id,
            self.instrument.alias,
            str(client_host),
            int(client_port),
            self.instrument.proxyHost,
            self.instrument.proxyPort,
            self.instrument.realHost,
            self.instrument.realPort,
        )

    def _finish_session_record(self) -> None:
        if self.repository:
            self.repository.finish_tcp_session(self.session_id)

    def _next_seq_no(self) -> int:
        with self._seq_lock:
            self._seq_no += 1
            return self._seq_no

    def _record_recv_frame(
        self,
        direction: str,
        data: bytes,
        delay_ms: int,
        frame_type: str,
        parsed_command: str = "",
        command_key: str = "",
        text_preview: str = "",
    ) -> None:
        if not self.repository:
            return
        context = self.runtime_context.snapshot()
        peer_host, peer_port = self._peer_for_direction(direction)
        seq_no = self._next_seq_no()
        if frame_type == "raw_recv":
            self._log_raw_stream(direction, data, seq_no)
        self.repository.insert_raw_stream_frame(
            session_id=self.session_id,
            seq_no=seq_no,
            instrument_alias=self.instrument.alias,
            direction=direction,
            protocol=self.instrument.protocol,
            payload_format=self.instrument.payloadFormat,
            data=data,
            product_name=context["product_name"],
            process_station=context["process_station"],
            product_code=context["product_code"],
            tu_name=context["tu_name"],
            profile_name=context["profile_name"],
            test_item_code=context["test_item_code"],
            peer_host=peer_host,
            peer_port=peer_port,
            frame_type=frame_type,
            parsed_command=parsed_command,
            command_key=command_key,
            text_preview=text_preview,
            delay_ms_from_prev=delay_ms,
        )

    def _log_raw_stream(
        self,
        direction: str,
        data: bytes,
        seq_no: int | None = None,
    ) -> None:
        if seq_no is None:
            seq_no = self._next_seq_no()
        logger.info("%s %r", direction, data)

    def _peer_for_direction(self, direction: str) -> tuple[str, int]:
        if direction == "TX":
            try:
                host, port = self.client_socket.getpeername()
                return str(host), int(port)
            except OSError:
                return "", 0
        return self.instrument.realHost, self.instrument.realPort

    def _remember_request(self, data: bytes) -> None:
        try:
            payload = PayloadCodec.decode(data, self.instrument.payloadFormat)
        except Exception:
            payload = PayloadCodec.decode(data, PayloadFormat.BINARY)
        context = self.runtime_context.snapshot()
        call_index = self.runtime_context.next_scene_record_call_index(
            context["product_name"],
            context["process_station"],
            context["product_code"],
            context["tu_name"],
            self.instrument.alias,
            payload.hash,
        )
        with self._record_lock:
            self._last_request_payload = payload
            self._last_request_context = context
            self._last_request_call_index = call_index

    def _record_compat_interaction(self, response: bytes) -> None:
        with self._record_lock:
            request_payload = self._last_request_payload
            context = self._last_request_context
            call_index = self._last_request_call_index
        if not request_payload or not context:
            return
        try:
            response_payload = PayloadCodec.decode(response, self.instrument.payloadFormat)
        except Exception:
            response_payload = PayloadCodec.decode(response, PayloadFormat.BINARY)
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
            delay_ms=0,
        ))

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
