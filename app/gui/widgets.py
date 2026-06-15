from __future__ import annotations

from PySide6.QtWidgets import QComboBox


def combo(values: list[str], current: str = "") -> QComboBox:
    widget = QComboBox()
    widget.addItems(values)
    if current in values:
        widget.setCurrentText(current)
    return widget
