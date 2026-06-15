from __future__ import annotations

import json
import logging
import socket
import threading
from collections.abc import Callable

from app.recorder.runtime_context import RuntimeContext

logger = logging.getLogger(__name__)


class ContextControlServer:
    def __init__(
        self,
        host: str,
        port: int,
        runtime_context: RuntimeContext,
        on_context_changed: Callable[[dict[str, str]], None] | None = None,
    ):
        self.host = host
        self.port = port
        self.runtime_context = runtime_context
        self.on_context_changed = on_context_changed
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None

    def start(self) -> None:
        if self.is_running():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._serve, name="ContextControlServer", daemon=True)
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
            server.bind((self.host, self.port))
            server.listen()
            server.settimeout(0.5)
            logger.info("Context control listening %s:%s", self.host, self.port)
            while not self._stop.is_set():
                try:
                    client, addr = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                threading.Thread(target=self._handle_client, args=(client, addr), daemon=True).start()

    def _handle_client(self, client: socket.socket, addr) -> None:
        with client:
            try:
                data = client.recv(4096).decode("utf-8", errors="replace").strip()
                if not data:
                    return
                notice = self._parse_notice(data)
                self.runtime_context.update_from_notice(notice)
                if self.on_context_changed:
                    self.on_context_changed(notice)
                client.sendall(b"OK\n")
                logger.info("Context notice from %s: %s", addr, notice)
            except Exception as exc:
                logger.exception("Invalid context notice from %s", addr)
                try:
                    client.sendall(f"ERROR {exc}\n".encode("utf-8", errors="replace"))
                except OSError:
                    pass

    def _parse_notice(self, data: str) -> dict[str, str]:
        if data.startswith("{"):
            parsed = json.loads(data)
            return {str(key): str(value) for key, value in parsed.items() if value is not None}
        result = {}
        for chunk in data.replace("\n", ";").split(";"):
            if "=" in chunk:
                key, value = chunk.split("=", 1)
                result[key.strip()] = value.strip()
        if not result and data:
            result["tuName"] = data
        return result
