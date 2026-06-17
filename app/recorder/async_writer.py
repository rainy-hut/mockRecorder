from __future__ import annotations

import logging
import queue
import threading

from app.db.repository import Repository
from app.recorder.record_event import RecordEvent

logger = logging.getLogger(__name__)


class AsyncWriter:
    def __init__(self, repository: Repository):
        self.repository = repository
        self.queue: queue.Queue[RecordEvent | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="AsyncWriter", daemon=True)
        self._running = threading.Event()

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._thread.start()

    def submit(self, event: RecordEvent) -> None:
        self.queue.put(event)

    def stop(self) -> None:
        self.queue.put(None)
        self.queue.join()
        self._running.clear()

    def _run(self) -> None:
        while True:
            event = self.queue.get()
            try:
                if event is None:
                    return
                self.repository.insert_interaction(event)
                logger.debug("Recorded interaction %s %s call=%s", event.instrument_alias, event.request_hash, event.call_index)
            except Exception:
                logger.exception("SQLite write failed")
            finally:
                self.queue.task_done()
