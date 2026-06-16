import html
import logging

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget


LOG_QSS = """
QWidget#LogPage {
    background: #F5F7FA;
}
QFrame#LogCard {
    background: #FFFFFF;
    border: 1px solid #DDE3EA;
    border-radius: 12px;
}
QComboBox, QLineEdit {
    min-height: 36px;
    background: #FFFFFF;
    border: 1px solid #D0D7E2;
    border-radius: 6px;
    padding: 0 10px;
}
QPushButton {
    min-height: 36px;
    border-radius: 6px;
    padding: 0 14px;
    font-weight: 600;
}
QPushButton#SecondaryButton {
    background: #FFFFFF;
    color: #2563EB;
    border: 1px solid #AFC3F6;
}
QTextEdit#LogText {
    background: #0B1020;
    color: #D1D5DB;
    border: 1px solid #111827;
    border-radius: 8px;
    font-family: Menlo, Consolas, monospace;
    font-size: 12px;
}
"""


class LogPage(QWidget):
    def __init__(self, log_path):
        super().__init__()
        self.setObjectName("LogPage")
        self.setStyleSheet(LOG_QSS)
        self.log_path = log_path
        self.raw_text = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        card = QFrame()
        card.setObjectName("LogCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        toolbar = QHBoxLayout()
        self.level_filter = QComboBox()
        self.level_filter.addItems(["全部", "INFO", "WARN", "ERROR"])
        self.level_filter.currentTextChanged.connect(self.render)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索日志")
        self.search.textChanged.connect(self.render)
        self.pause = QCheckBox("暂停滚动")
        clear = QPushButton("清空显示")
        clear.setObjectName("SecondaryButton")
        clear.clicked.connect(self.clear)
        export = QPushButton("导出日志")
        export.setObjectName("SecondaryButton")
        export.clicked.connect(self.save)
        toolbar.addWidget(self.level_filter)
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(self.pause)
        toolbar.addWidget(clear)
        toolbar.addWidget(export)
        card_layout.addLayout(toolbar)

        self.text = QTextEdit()
        self.text.setObjectName("LogText")
        self.text.setReadOnly(True)
        card_layout.addWidget(self.text, 1)
        layout.addWidget(card, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)
        self.refresh()

    def refresh(self) -> None:
        if self.log_path.exists():
            self.raw_text = self.log_path.read_text(encoding="utf-8", errors="replace")[-50000:]
            self.render()

    def render(self) -> None:
        level = self.level_filter.currentText()
        keyword = self.search.text().strip().lower()
        lines = []
        for line in self.raw_text.splitlines():
            upper = line.upper()
            if level == "INFO" and " INFO " not in upper:
                continue
            if level == "WARN" and " WARNING " not in upper and " WARN " not in upper:
                continue
            if level == "ERROR" and " ERROR " not in upper:
                continue
            if keyword and keyword not in line.lower():
                continue
            color = "#D1D5DB"
            if " ERROR " in upper:
                color = "#FCA5A5"
            elif " WARNING " in upper or " WARN " in upper:
                color = "#FCD34D"
            elif " INFO " in upper:
                color = "#93C5FD"
            lines.append(f'<span style="color:{color};">{html.escape(line)}</span>')
        self.text.setHtml("<br>".join(lines))
        if not self.pause.isChecked():
            self.text.moveCursor(QTextCursor.End)

    def clear(self) -> None:
        self.raw_text = ""
        self.text.clear()
        if not self.log_path.exists():
            return
        for handler in logging.getLogger().handlers:
            if hasattr(handler, "flush"):
                handler.flush()
        self.log_path.write_text("", encoding="utf-8")

    def save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", "app.log", "Log (*.log);;Text (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.raw_text or self.text.toPlainText())
