from __future__ import annotations

import logging

from app.constants import ProtocolType
from app.models import AppConfig
from app.proxy.replay_engine import ReplayEngine
from app.proxy.tcp_proxy_server import TcpProxyServer
from app.recorder.recorder_service import RecorderService
from app.recorder.runtime_context import RuntimeContext

logger = logging.getLogger(__name__)


class ProxyManager:
    def __init__(self, app_config: AppConfig, runtime_context: RuntimeContext, recorder_service: RecorderService, replay_engine: ReplayEngine):
        self.app_config = app_config
        self.runtime_context = runtime_context
        self.recorder_service = recorder_service
        self.replay_engine = replay_engine
        self.servers: list[TcpProxyServer] = []
        self.warnings: list[str] = []

    def start(self) -> list[str]:
        self.stop()
        self.warnings = []
        for instrument in self.app_config.instruments:
            if not instrument.enabled:
                continue
            if instrument.protocol == ProtocolType.VISA_INSTR_RESERVED:
                msg = f"{instrument.alias}: VISA_INSTR_RESERVED 第一版不支持透明代理。请改用 VISA_SOCKET 或 SOCKET 方式。"
                logger.debug(msg)
                self.warnings.append(msg)
                continue
            server = TcpProxyServer(instrument, self.app_config, self.runtime_context, self.recorder_service, self.replay_engine)
            server.start()
            self.servers.append(server)
        return self.warnings

    def stop(self) -> None:
        for server in self.servers:
            server.stop()
        self.servers = []

    def is_running(self) -> bool:
        return any(server.is_running() for server in self.servers)

    def status(self) -> list[dict[str, object]]:
        return [{"alias": s.instrument.alias, "running": s.is_running(), "port": s.instrument.proxyPort} for s in self.servers]
