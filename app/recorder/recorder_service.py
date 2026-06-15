from app.recorder.async_writer import AsyncWriter
from app.recorder.record_event import RecordEvent


class RecorderService:
    def __init__(self, writer: AsyncWriter):
        self.writer = writer

    def record(self, event: RecordEvent) -> None:
        self.writer.submit(event)
