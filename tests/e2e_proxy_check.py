import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.constants import Mode, PayloadFormat, ProtocolType
from app.db.database import Database
from app.db.repository import Repository
from app.models import AppConfig, InstrumentConfig
from app.proxy.proxy_manager import ProxyManager
from app.proxy.replay_engine import ReplayEngine
from app.recorder.async_writer import AsyncWriter
from app.recorder.recorder_service import RecorderService
from app.recorder.runtime_context import RuntimeContext


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def main() -> None:
    real_port = _free_port()
    proxy_port = _free_port()
    stop_fake = threading.Event()

    def fake_instrument() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", real_port))
            server.listen()
            server.settimeout(0.2)
            while not stop_fake.is_set():
                try:
                    client, _ = server.accept()
                except socket.timeout:
                    continue
                with client:
                    data = b""
                    while not data.endswith(b"\n"):
                        part = client.recv(1)
                        if not part:
                            break
                        data += part
                    if data == b"*IDN?\n":
                        client.sendall(b"MOCK,SA,001\n")

    thread = threading.Thread(target=fake_instrument, daemon=True)
    thread.start()
    time.sleep(0.1)

    try:
        with tempfile.TemporaryDirectory(dir="/Users/yangqi/Documents/mockRecorder") as temp_dir:
            repo = Repository(Database(Path(temp_dir) / "recorder.db"))
            repo.init_schema()
            instrument = InstrumentConfig(
                alias="SA_E2E",
                type="SpectrumAnalyzer",
                protocol=ProtocolType.SOCKET_SCPI_LINE,
                payloadFormat=PayloadFormat.TEXT,
                proxyHost="127.0.0.1",
                proxyPort=proxy_port,
                realHost="127.0.0.1",
                realPort=real_port,
                enabled=True,
            )
            config = AppConfig(
                mode=Mode.RECORD,
                currentProfile="default",
                currentTestItemCode="DEFAULT_TEST",
                currentVariant="normal",
                instruments=[instrument],
            )
            context = RuntimeContext(
                mode=Mode.RECORD,
                profile_name="default",
                test_item_code="DEFAULT_TEST",
                variant_name="normal",
            )
            writer = AsyncWriter(repo)
            writer.start()
            recorder = RecorderService(writer)
            replay = ReplayEngine(repo, context, append_new_line=True)
            manager = ProxyManager(config, context, recorder, replay)
            manager.start()
            time.sleep(0.1)

            with socket.create_connection(("127.0.0.1", proxy_port), timeout=2) as client:
                client.sendall(b"*IDN?\n")
                response = client.recv(1024)
            assert response == b"MOCK,SA,001\n", response
            writer.queue.join()
            assert repo.count_interactions({"instrument_alias": "SA_E2E"}) == 1

            context.set_mode(Mode.REPLAY)
            with socket.create_connection(("127.0.0.1", proxy_port), timeout=2) as client:
                client.sendall(b"*IDN?\n")
                replayed = client.recv(1024)
            assert replayed == b"MOCK,SA,001\n", replayed

            manager.stop()
            writer.stop()
    finally:
        stop_fake.set()

    print("proxy record/replay e2e passed", "real_port", real_port, "proxy_port", proxy_port)


if __name__ == "__main__":
    main()
