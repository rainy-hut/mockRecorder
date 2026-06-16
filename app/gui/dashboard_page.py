from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.constants import Mode


class DashboardPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent_window = parent
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("运行控制")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("确认当前业务模式和测试场景后，启动代理即可开始录制或回放。")
        subtitle.setObjectName("SubtleText")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        mode_cards = QHBoxLayout()
        mode_cards.setSpacing(14)
        self.mode_cards = {}
        mode_cards.addWidget(self._mode_card(Mode.RECORD, "录制模式", "连接真实仪器，保存测试过程中的交互数据。", lambda: parent.set_mode(Mode.RECORD)))
        mode_cards.addWidget(self._mode_card(Mode.REPLAY, "回放模式", "使用历史数据模拟仪器响应，无需真实硬件。", lambda: parent.set_mode(Mode.REPLAY)))
        mode_cards.addWidget(self._mode_card(Mode.OFF, "旁路模式", "只转发请求，不保存录制数据。", lambda: parent.set_mode(Mode.OFF)))
        layout.addLayout(mode_cards)

        status_box = QFrame()
        status_box.setObjectName("Panel")
        status_layout = QGridLayout(status_box)
        self.labels = {}
        rows = [
            ("mode", "业务模式"),
            ("proxy", "代理服务"),
            ("control", "测试项通知"),
            ("scene", "当前场景"),
            ("tu_name", "当前测试项"),
            ("instrument_count", "仪器映射数量"),
            ("interaction_count", "录制数据量"),
            ("database", "数据库路径"),
        ]
        for row, (key, title_text) in enumerate(rows):
            name = QLabel(title_text)
            name.setObjectName("FieldName")
            value = QLabel("-")
            value.setTextInteractionFlags(value.textInteractionFlags() | Qt.TextSelectableByMouse)
            if key == "database":
                value.setTextFormat(Qt.PlainText)
                value.setWordWrap(False)
            value.setTextInteractionFlags(value.textInteractionFlags() | Qt.TextSelectableByMouse)
            self.labels[key] = value
            status_layout.addWidget(name, row, 0)
            status_layout.addWidget(value, row, 1)
        layout.addWidget(status_box)

        buttons = QHBoxLayout()
        for text, slot, kind in [
            ("开始录制/回放", parent.start_proxy, "PrimaryButton"),
            ("停止录制/回放", parent.stop_proxy, "DangerButton"),
            ("查看录制数据", parent.show_records, "SecondaryButton"),
            ("重置回放计数器", parent.reset_replay_counter, "SecondaryButton"),
        ]:
            button = QPushButton(text)
            button.setObjectName(kind)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addStretch(1)

    def _mode_card(self, mode: str, title: str, body: str, slot) -> QFrame:
        card = QFrame()
        card.setObjectName("ModeCard")
        box = QVBoxLayout(card)
        head = QHBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("CardTitle")
        badge = QLabel("")
        badge.setObjectName("ModeBadge")
        badge.hide()
        head.addWidget(heading)
        head.addStretch(1)
        head.addWidget(badge)
        text = QLabel(body)
        text.setObjectName("SubtleText")
        text.setWordWrap(True)
        button = QPushButton(f"选择{title}")
        button.setObjectName("SecondaryButton")
        button.clicked.connect(slot)
        box.addLayout(head)
        box.addWidget(text)
        box.addStretch(1)
        box.addWidget(button)
        self.mode_cards[mode] = (card, badge, button)
        return card

    def refresh(self, data: dict[str, object]) -> None:
        for key, value in data.items():
            if key in self.labels:
                text = str(value)
                self.labels[key].setText(text)
                if key == "database":
                    self.labels[key].setToolTip(text)
        mode = str(data.get("mode", ""))
        for key, (card, badge, button) in self.mode_cards.items():
            active = key == mode
            card.setObjectName("ActiveModeCard" if active else "ModeCard")
            badge.setText("当前模式")
            badge.setVisible(active)
            button.setEnabled(not active)
            card.style().unpolish(card)
            card.style().polish(card)
