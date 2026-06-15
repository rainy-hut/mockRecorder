from __future__ import annotations

import logging
import socket
import threading

from app.models import AppConfig, InstrumentConfig
from app.proxy.replay_engine import ReplayEngine
from app.proxy.tcp_proxy_session import TcpProxySession
from app.recorder.recorder_service import RecorderService
from app.recorder.runtime_context import RuntimeContext

logger = logging.getLogger(__name__)


class TcpProxyServer:
    def __init__(
        self,
        instrument: InstrumentConfig,
        app_config: AppConfig,
        runtime_context: RuntimeContext,
        recorder_service: RecorderService,
        replay_engine: ReplayEngine,
    ):
        self.instrument = instrument
        self.app_config = app_config
        self.runtime_context = runtime_context
        self.recorder_service = recorder_service
        self.replay_engine = replay_engine
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._serve, name=f"Proxy-{self.instrument.alias}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=2)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _serve(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            self._sock = server
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.instrument.proxyHost, self.instrument.proxyPort))
            server.listen()
            server.settimeout(0.5)
            logger.info("Proxy listening %s %s:%s", self.instrument.alias, self.instrument.proxyHost, self.instrument.proxyPort)
            while not self._stop.is_set():
                try:
                    client, addr = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                logger.info("Client connected %s from %s", self.instrument.alias, addr)
                session = TcpProxySession(client, self.instrument, self.app_config, self.runtime_context, self.recorder_service, self.replay_engine)
                threading.Thread(target=session.run, name=f"Session-{self.instrument.alias}", daemon=True).start()
