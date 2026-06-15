from __future__ import annotations

import socket

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.constants import PayloadFormat, ProtocolType
from app.models import InstrumentConfig


class InstrumentPage(QWidget):
    HEADERS = ["序号", "启用", "仪器", "组件访问地址", "真实仪器地址", "连接方式", "操作"]
    PROTOCOL_LABELS = {
        "SCPI Socket": ProtocolType.SOCKET_SCPI_LINE,
        "原始 Socket": ProtocolType.SOCKET_RAW,
        "VISA Socket": ProtocolType.VISA_SOCKET,
        "厂商/VISA专用": ProtocolType.VISA_INSTR_RESERVED,
    }
    PROTOCOL_NAMES = {value: key for key, value in PROTOCOL_LABELS.items()}

    def __init__(self, parent):
        super().__init__()
        self.parent_window = parent
        self.dirty = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("ConfigCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("仪器 IP 映射配置")
        title.setObjectName("ConfigCardTitle")
        self.status = QLabel("已保存")
        self.status.setObjectName("SavedBadge")
        header.addWidget(title)
        header.addWidget(self.status)
        header.addStretch(1)
        add = QPushButton("新增仪器")
        add.setObjectName("SecondaryButton")
        add.clicked.connect(self.add_row)
        test = QPushButton("测试连接")
        test.setObjectName("SecondaryButton")
        test.clicked.connect(self.test_selected_connection)
        save = QPushButton("保存映射")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self.save)
        header.addWidget(add)
        header.addWidget(test)
        header.addWidget(save)
        card_layout.addLayout(header)

        hint = QLabel("提示：组件访问地址是被测服务连接的地址，真实仪器地址是实际硬件地址。禁用后不会启动该仪器代理。")
        hint.setObjectName("MutedText")
        card_layout.addWidget(hint)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self.mark_dirty)
        card_layout.addWidget(self.table, 1)
        layout.addWidget(card)

    def load_instruments(self, instruments: list[InstrumentConfig]) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for config in instruments:
            self.add_row(config, mark_dirty=False)
        self.table.blockSignals(False)
        self.set_dirty(False)

    def add_row(self, config: InstrumentConfig | None = None, mark_dirty: bool = True) -> None:
        config = config or InstrumentConfig(alias=f"INST_{self.table.rowCount() + 1:02d}", realHost="192.168.1.20")
        row = self.table.rowCount()
        self.table.insertRow(row)
        index = QTableWidgetItem(str(row + 1))
        index.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.table.setItem(row, 0, index)
        enabled = QTableWidgetItem("")
        enabled.setCheckState(Qt.CheckState.Checked if config.enabled else Qt.CheckState.Unchecked)
        self.table.setItem(row, 1, enabled)
        self.table.setItem(row, 2, QTableWidgetItem(config.alias))
        self._set_address_item(row, 3, f"{config.proxyHost}:{config.proxyPort}")
        self._set_address_item(row, 4, f"{config.realHost}:{config.realPort}")
        protocol = QComboBox()
        protocol.addItems(list(self.PROTOCOL_LABELS.keys()))
        protocol.setCurrentText(self.PROTOCOL_NAMES.get(config.protocol, "SCPI Socket"))
        protocol.currentTextChanged.connect(lambda _text: self.set_dirty(True))
        self.table.setCellWidget(row, 5, protocol)
        self.table.setCellWidget(row, 6, self._row_actions(row))
        self.apply_column_widths()
        if mark_dirty:
            self.set_dirty(True)

    def delete_selected(self) -> None:
        row = self.table.currentRow()
        self.delete_row(row)

    def delete_row(self, row: int) -> None:
        if row < 0 or row >= self.table.rowCount():
            return
        alias = self._text(row, 2) or f"第 {row + 1} 行"
        if QMessageBox.question(self, "确认删除", f"确认删除仪器映射 {alias}？") == QMessageBox.Yes:
            self.table.removeRow(row)
            self.renumber_rows()
            self.set_dirty(True)

    def collect(self) -> list[InstrumentConfig]:
        instruments = []
        for row in range(self.table.rowCount()):
            alias = self._text(row, 2) or f"INST_{row + 1:02d}"
            proxy_host, proxy_port = self._parse_address(self._text(row, 3), "127.0.0.1", 15026 + row)
            real_host, real_port = self._parse_address(self._text(row, 4), "", 5025)
            protocol_widget = self.table.cellWidget(row, 5)
            protocol_label = protocol_widget.currentText() if isinstance(protocol_widget, QComboBox) else "SCPI Socket"
            protocol_value = self.PROTOCOL_LABELS.get(protocol_label, ProtocolType.SOCKET_SCPI_LINE)
            enabled_item = self.table.item(row, 1)
            instruments.append(InstrumentConfig(
                alias=alias,
                type="",
                protocol=protocol_value,
                payloadFormat=PayloadFormat.HEX_TEXT if protocol_value == ProtocolType.SOCKET_RAW else PayloadFormat.TEXT,
                proxyHost=proxy_host,
                proxyPort=proxy_port,
                realHost=real_host,
                realPort=real_port,
                visaResource="",
                enabled=enabled_item.checkState() == Qt.CheckState.Checked if enabled_item else True,
            ))
        return instruments

    def save(self) -> None:
        try:
            instruments = self.collect()
            for item in instruments:
                if not item.realHost and item.protocol != ProtocolType.VISA_INSTR_RESERVED:
                    raise ValueError(f"{item.alias} 缺少真实仪器地址")
            self.parent_window.save_instruments(instruments)
            self.set_dirty(False)
            QMessageBox.information(self, "保存成功", "映射配置已保存")
        except Exception as exc:
            QMessageBox.warning(self, "配置错误", str(exc))

    def test_selected_connection(self) -> None:
        row = self.table.currentRow()
        self.test_row(row)

    def test_row(self, row: int) -> None:
        if row < 0 or row >= self.table.rowCount():
            QMessageBox.information(self, "测试连接", "请先选择一条仪器映射")
            return
        try:
            config = self.collect()[row]
            if not config.enabled:
                QMessageBox.information(self, "测试连接", "该映射已禁用，启用后再测试连接。")
                return
            with socket.create_connection((config.realHost, config.realPort), timeout=2):
                pass
            QMessageBox.information(self, "测试连接", f"{config.realHost}:{config.realPort} 连接成功")
        except Exception as exc:
            QMessageBox.warning(self, "测试连接失败", str(exc))

    def mark_dirty(self) -> None:
        self.set_dirty(True)

    def set_dirty(self, dirty: bool) -> None:
        self.dirty = dirty
        self.status.setText("有未保存修改" if dirty else "已保存")
        self.status.setObjectName("DirtyBadge" if dirty else "SavedBadge")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        if dirty:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item and not item.text().startswith("● "):
                    item.setText(f"● {row + 1}")
                    item.setBackground(Qt.GlobalColor.yellow)
        else:
            self.renumber_rows()

    def renumber_rows(self) -> None:
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setText(str(row + 1))
                item.setBackground(QBrush())
            self.table.setCellWidget(row, 6, self._row_actions(row))
        self.table.blockSignals(False)

    def apply_column_widths(self) -> None:
        widths = [50, 70, 160, 260, 260, 180, 140]
        for col, width in enumerate(widths):
            self.table.setColumnWidth(col, width)

    def _row_actions(self, row: int) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        test = QPushButton("测试")
        test.setObjectName("SecondaryButton")
        test.clicked.connect(lambda _checked=False, r=row: self.test_row(r))
        delete = QPushButton("删除")
        delete.setObjectName("DangerButton")
        delete.clicked.connect(lambda _checked=False, r=row: self.delete_row(r))
        layout.addWidget(test)
        layout.addWidget(delete)
        return widget

    def _set_address_item(self, row: int, col: int, value: str) -> None:
        item = QTableWidgetItem(value)
        item.setToolTip(value)
        self.table.setItem(row, col, item)

    def _text(self, row: int, col: int) -> str:
        item = self.table.item(row, col)
        return item.text().replace("●", "").strip() if item else ""

    def _parse_address(self, value: str, default_host: str, default_port: int) -> tuple[str, int]:
        if not value:
            return default_host, default_port
        if ":" not in value:
            return value.strip(), default_port
        host, port = value.rsplit(":", 1)
        return host.strip(), int(port.strip())
