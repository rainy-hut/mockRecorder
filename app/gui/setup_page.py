from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.gui.context_page import ContextPage
from app.gui.instrument_page import InstrumentPage

SETUP_QSS = """
QWidget#SetupPage {
    background: #F5F7FA;
    color: #1F2937;
}
QLabel#SetupTitle {
    font-size: 28px;
    font-weight: 700;
    color: #1F2937;
}
QLabel#SubtleText, QLabel#MutedText {
    color: #6B7280;
}
QLabel#ConfigCardTitle {
    font-size: 16px;
    font-weight: 700;
    color: #1F2937;
}
QLabel#SavedBadge {
    background: #DCFCE7;
    color: #16A34A;
    border: 1px solid #BBF7D0;
    border-radius: 10px;
    padding: 2px 10px;
    font-weight: 700;
}
QLabel#DirtyBadge {
    background: #FEF3C7;
    color: #92400E;
    border: 1px solid #FDE68A;
    border-radius: 10px;
    padding: 2px 10px;
    font-weight: 700;
}
QLabel#FieldLabel {
    color: #374151;
    font-size: 14px;
    font-weight: 600;
}
QFrame#ConfigCard {
    background: #FFFFFF;
    border: 1px solid #DDE3EA;
    border-radius: 12px;
}
QLineEdit, QComboBox {
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
QPushButton#PrimaryButton {
    background: #2563EB;
    color: white;
    border: 1px solid #2563EB;
}
QPushButton#PrimaryButton:hover {
    background: #1D4ED8;
    border-color: #1D4ED8;
}
QPushButton#SecondaryButton {
    background: #FFFFFF;
    color: #2563EB;
    border: 1px solid #AFC3F6;
}
QPushButton#SecondaryButton:hover {
    background: #EFF6FF;
}
QPushButton#DangerButton {
    background: #FFFFFF;
    color: #DC2626;
    border: 1px solid #F3B4B4;
}
QPushButton#DangerButton:hover {
    background: #FEF2F2;
}
QTableWidget {
    background: #FFFFFF;
    alternate-background-color: #F8FAFC;
    border: 1px solid #DDE3EA;
    border-radius: 8px;
    gridline-color: #E5EAF1;
    selection-background-color: #DBEAFE;
    selection-color: #1F2937;
}
QHeaderView::section {
    background: #EEF3F8;
    color: #374151;
    border: 0;
    border-right: 1px solid #DDE3EA;
    padding: 8px;
    font-weight: 700;
}
"""


class SetupPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.setObjectName("SetupPage")
        self.setStyleSheet(SETUP_QSS)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        title = QLabel("基础配置")
        title.setObjectName("SetupTitle")
        hint = QLabel("配置当前测试场景信息，并维护各仪器代理的组件访问地址与真实硬件地址。运行控制页面会读取这些配置。")
        hint.setObjectName("SubtleText")
        layout.addWidget(title)
        layout.addWidget(hint)
        self.context_page = ContextPage(parent)
        self.instrument_page = InstrumentPage(parent)
        layout.addWidget(self.context_page)
        layout.addWidget(self.instrument_page, 1)

    def load(self, config) -> None:
        self.context_page.load_values(config)
        self.instrument_page.load_instruments(config.instruments)

    def load_runtime_context(self, snapshot: dict[str, str]) -> None:
        self.context_page.load_runtime_context(snapshot)
