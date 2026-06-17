from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


PAGE_QSS = """
QWidget#RecordBrowserPage {
    background: #F5F7FA;
    color: #1F2937;
}
QLabel#PageTitle {
    font-size: 28px;
    font-weight: 700;
    color: #1F2937;
}
QLabel#CardTitle {
    font-size: 16px;
    font-weight: 700;
    color: #1F2937;
}
QLabel#FieldLabel {
    background: transparent;
    font-size: 14px;
    color: #374151;
    font-weight: 600;
}
QLabel#MutedText {
    color: #6B7280;
}
QLabel#StatusText {
    color: #6B7280;
    font-weight: 600;
}
QFrame#Card {
    background: #FFFFFF;
    border: 1px solid #DDE3EA;
    border-radius: 12px;
}
QPushButton {
    min-height: 34px;
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
QPushButton#PrimaryButton:disabled,
QPushButton#SecondaryButton:disabled,
QPushButton#DangerButton:disabled {
    background: #F3F4F6;
    color: #9CA3AF;
    border: 1px solid #E5E7EB;
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
QPushButton#TabButton {
    background: #FFFFFF;
    color: #6B7280;
    border: 1px solid #DDE3EA;
    min-width: 104px;
}
QPushButton#TabButton:checked {
    background: #2563EB;
    color: white;
    border-color: #2563EB;
}
QLineEdit, QComboBox, QSpinBox {
    min-height: 34px;
    background: #FFFFFF;
    border: 1px solid #D0D7E2;
    border-radius: 6px;
    padding: 0 10px;
}
QTextEdit {
    background: #FFFFFF;
    border: 1px solid #D0D7E2;
    border-radius: 6px;
    padding: 8px;
}
QTableWidget {
    background: #FFFFFF;
    alternate-background-color: #F8FAFC;
    gridline-color: #E5EAF1;
    border: 1px solid #DDE3EA;
    border-radius: 8px;
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


class RecordBrowserPage(QWidget):
    COLUMNS = [
        ("_selected", "选择"),
        ("product_name", "产品"),
        ("process_station", "工序工位"),
        ("product_code", "编码"),
        ("tu_name", "测试项"),
        ("instrument_alias", "仪器"),
        ("request_text", "请求文本"),
        ("response_text", "响应文本"),
        ("call_index", "调用序号"),
        ("success", "成功"),
    ]

    EDIT_FIELDS = [
        ("product_name", "产品"),
        ("process_station", "工序工位"),
        ("product_code", "编码"),
        ("tu_name", "测试项"),
        ("instrument_alias", "仪器别名"),
        ("protocol", "协议"),
        ("payload_format", "码流格式"),
        ("request_text", "请求文本"),
        ("request_hex", "请求HEX"),
        ("request_hash", "请求Hash"),
        ("response_text", "响应文本"),
        ("response_hex", "响应HEX"),
        ("call_index", "调用序号"),
        ("replay_strategy", "回放策略"),
        ("success", "成功"),
        ("remark", "备注"),
    ]

    def __init__(self, parent):
        super().__init__()
        self.setObjectName("RecordBrowserPage")
        self.parent_window = parent
        self.rows = []
        self.page = 1
        self.total = 0
        self.current_query_mode = "normal"
        self.apply_styles()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        layout.addLayout(self.create_header_area())
        layout.addLayout(self.create_query_tabs())
        self.query_stack = QStackedWidget()
        self.query_stack.addWidget(self.create_filter_card())
        self.query_stack.addWidget(self.create_sql_card())
        layout.addWidget(self.query_stack)
        layout.addWidget(self.create_table_area(), 1)

    def create_header_area(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        title = QLabel("录制数据查询")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        layout.addStretch(1)
        self.status_label = QLabel("状态：就绪")
        self.status_label.setObjectName("StatusText")
        layout.addWidget(self.status_label)
        return layout

    def create_query_tabs(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        self.normal_tab = QPushButton("普通查询")
        self.sql_tab = QPushButton("SQL 查询")
        for button in [self.normal_tab, self.sql_tab]:
            button.setCheckable(True)
            button.setObjectName("TabButton")
        self.normal_tab.setChecked(True)
        self.normal_tab.clicked.connect(lambda: self.switch_query_mode("normal"))
        self.sql_tab.clicked.connect(lambda: self.switch_query_mode("sql"))
        layout.addWidget(self.normal_tab)
        layout.addWidget(self.sql_tab)
        layout.addStretch(1)
        return layout

    def create_filter_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)
        layout.addWidget(self._card_title("查询条件"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)
        self.filter_inputs = {}
        fields = [
            ("product_name", "产品", QLineEdit()),
            ("process_station", "工序工位", QLineEdit()),
            ("product_code", "编码", QLineEdit()),
            ("tu_name", "测试项", QLineEdit()),
            ("instrument_alias", "仪器", QLineEdit()),
            ("request_text", "请求文本", QLineEdit()),
            ("success", "成功状态", QComboBox()),
        ]
        for index, (key, label_text, widget) in enumerate(fields):
            if isinstance(widget, QComboBox):
                widget.addItem("全部", "")
                widget.addItem("成功", "1")
                widget.addItem("失败", "0")
            self.filter_inputs[key] = widget
            if index < 6:
                row = index // 3
                col = index % 3
                grid.addWidget(self._field_label(label_text), row * 2, col)
                grid.addWidget(widget, row * 2 + 1, col)

        grid.addWidget(self._field_label("成功状态"), 4, 0)
        grid.addWidget(self.filter_inputs["success"], 5, 0)
        self.query_button = self._button("查询", "primary")
        self.query_button.setFixedWidth(108)
        self.query_button.clicked.connect(self.first_page)
        reset = self._button("重置", "secondary")
        reset.setFixedWidth(108)
        reset.clicked.connect(self.reset_filters)
        grid.addWidget(self.query_button, 5, 1)
        grid.addWidget(reset, 5, 2)
        layout.addLayout(grid)
        return card

    def create_sql_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(self._card_title("SQL 查询"))
        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText("输入 SELECT / INSERT / UPDATE / DELETE 语句，作用于当前 SQLite 数据库")
        self.sql_editor.setMinimumHeight(64)
        self.sql_editor.setMaximumHeight(92)
        self.sql_result = QTextEdit()
        self.sql_result.setReadOnly(True)
        self.sql_result.setMinimumHeight(56)
        self.sql_result.setMaximumHeight(88)
        run_sql = self._button("执行 SQL", "primary")
        run_sql.clicked.connect(self.execute_sql)
        layout.addWidget(self.sql_editor)
        layout.addWidget(run_sql, alignment=Qt.AlignLeft)
        layout.addWidget(self.sql_result)
        return card

    def create_table_toolbar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        title = self._card_title("数据列表")
        layout.addWidget(title)
        layout.addStretch(1)
        self.create_button = self._button("新增", "primary")
        self.edit_button = self._button("编辑", "secondary")
        self.save_button = self._button("保存", "secondary")
        self.detail_button = self._button("详情", "secondary")
        self.delete_button = self._button("删除", "danger")
        for button, slot in [
            (self.create_button, self.create_record),
            (self.edit_button, self.edit_record),
            (self.save_button, self.edit_record),
            (self.detail_button, self.detail),
            (self.delete_button, self.delete),
        ]:
            button.clicked.connect(slot)
            layout.addWidget(button)
        return layout

    def create_table_area(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addLayout(self.create_table_toolbar())

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([title for _, title in self.COLUMNS])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setTextElideMode(Qt.ElideRight)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.update_action_states)
        self.table.itemChanged.connect(self.update_action_states)
        self.table.setMinimumHeight(220)
        self._apply_table_columns()
        layout.addWidget(self.table, 1)
        layout.addLayout(self.create_pagination_bar())
        self.update_action_states()
        return card

    def create_pagination_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addStretch(1)
        layout.addWidget(QLabel("每页"))
        self.page_size = QSpinBox()
        self.page_size.setRange(20, 1000)
        self.page_size.setValue(100)
        layout.addWidget(self.page_size)
        layout.addWidget(QLabel("条"))
        self.total_label = QLabel("共 0 条")
        self.page_label = QLabel("第 1 / 1 页")
        self.total_label.setObjectName("MutedText")
        self.page_label.setObjectName("MutedText")
        layout.addWidget(self.total_label)
        layout.addWidget(self.page_label)
        self.prev_button = self._button("上一页", "secondary")
        self.next_button = self._button("下一页", "secondary")
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        layout.addWidget(self.prev_button)
        layout.addWidget(self.next_button)
        return layout

    def apply_styles(self) -> None:
        self.setStyleSheet(PAGE_QSS)

    def switch_query_mode(self, mode: str) -> None:
        self.current_query_mode = mode
        is_normal = mode == "normal"
        self.normal_tab.setChecked(is_normal)
        self.sql_tab.setChecked(not is_normal)
        self.query_stack.setCurrentIndex(0 if is_normal else 1)

    def filters(self) -> dict[str, str]:
        result = {}
        for key, widget in self.filter_inputs.items():
            if isinstance(widget, QComboBox):
                value = widget.currentData()
            else:
                value = widget.text().strip()
            if value not in ("", None):
                result[key] = str(value)
        return result

    def refresh(self) -> None:
        try:
            filters = self.filters()
            limit = self.page_size.value()
            self.total = self.parent_window.repository.count_interactions(filters)
            max_page = max(1, (self.total + limit - 1) // limit)
            self.page = min(max(self.page, 1), max_page)
            offset = (self.page - 1) * limit
            self.rows = self.parent_window.repository.list_interactions(filters, limit=limit, offset=offset)
            self.table.setRowCount(0)
            self.table.clearSpans()
            if self.rows:
                self.table.blockSignals(True)
                for row_data in self.rows:
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    for col, (key, _) in enumerate(self.COLUMNS):
                        if key == "_selected":
                            item = QTableWidgetItem("")
                            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                            item.setCheckState(Qt.CheckState.Unchecked)
                            item.setData(Qt.UserRole, int(row_data["id"]))
                        else:
                            item = QTableWidgetItem(str(row_data[key] if row_data[key] is not None else ""))
                            item.setData(Qt.UserRole, int(row_data["id"]))
                        self.table.setItem(row, col, item)
                self.table.blockSignals(False)
            else:
                self.table.setRowCount(1)
                self.table.setSpan(0, 0, 1, len(self.COLUMNS))
                empty_item = QTableWidgetItem("暂无录制数据\n请设置查询条件后点击“查询”，或点击“新增”创建数据")
                empty_item.setTextAlignment(Qt.AlignCenter)
                empty_item.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(0, 0, empty_item)
                self.table.setRowHeight(0, 180)
            self.total_label.setText(f"共 {self.total} 条")
            self.page_label.setText(f"第 {self.page} / {max_page} 页")
            self.status_label.setText("状态：查询完成")
            self._apply_table_columns()
            self.update_action_states()
        except Exception as exc:
            self.status_label.setText("状态：查询失败")
            QMessageBox.warning(self, "查询失败", str(exc))

    def first_page(self) -> None:
        self.page = 1
        self.query_button.setEnabled(False)
        self.query_button.setText("查询中...")
        QApplication.processEvents()
        try:
            self.refresh()
        finally:
            self.query_button.setText("查询")
            self.query_button.setEnabled(True)

    def prev_page(self) -> None:
        self.page = max(1, self.page - 1)
        self.refresh()

    def next_page(self) -> None:
        limit = self.page_size.value()
        max_page = max(1, (self.total + limit - 1) // limit)
        self.page = min(max_page, self.page + 1)
        self.refresh()

    def reset_filters(self) -> None:
        for widget in self.filter_inputs.values():
            if isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            else:
                widget.clear()
        self.first_page()

    def current_record(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rows):
            return None
        return dict(self.rows[row])

    def checked_record_ids(self) -> list[int]:
        ids = []
        for row in range(len(self.rows)):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                ids.append(int(item.data(Qt.UserRole)))
        return ids

    def create_record(self) -> None:
        data = self._edit_dialog({
            "product_name": self.parent_window.app_config.currentProduct,
            "process_station": self.parent_window.app_config.currentProcessStation,
            "product_code": self.parent_window.app_config.currentProductCode,
            "tu_name": self.parent_window.runtime_context.snapshot()["tu_name"],
            "protocol": "SOCKET_SCPI_LINE",
            "payload_format": "TEXT",
            "call_index": "1",
            "replay_strategy": "BY_CALL_INDEX",
            "success": "1",
        }, "新增录制数据")
        if data is not None:
            self.parent_window.repository.insert_interaction_dict(data)
            self.status_label.setText("状态：新增成功")
            self.refresh()

    def edit_record(self) -> None:
        record = self.current_record()
        if not record:
            return
        data = self._edit_dialog(record, f"编辑录制数据 #{record['id']}")
        if data is not None:
            self.parent_window.repository.update_interaction(int(record["id"]), data)
            self.status_label.setText("状态：保存成功")
            self.refresh()

    def detail(self) -> None:
        record = self.current_record()
        if not record:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"录制数据详情 #{record['id']}")
        layout = QFormLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        labels = {
            "request_text": "完整请求文本",
            "response_text": "完整响应文本",
            "normalized_request": "标准化请求",
            "request_hash": "请求Hash",
            "request_hex": "请求HEX",
            "response_hex": "响应HEX",
            "response_hash": "响应Hash",
            "error_type": "错误类型",
            "error_message": "错误信息",
            "remark": "备注",
        }
        text.setPlainText("\n".join(f"{label}: {record.get(key) or ''}" for key, label in labels.items()))
        layout.addRow(text)
        dialog.resize(820, 520)
        dialog.exec()

    def delete(self) -> None:
        checked_ids = self.checked_record_ids()
        if checked_ids:
            count = len(checked_ids)
            if QMessageBox.question(self, "确认删除", f"确认删除已勾选的 {count} 条录制数据？") != QMessageBox.Yes:
                return
            for interaction_id in checked_ids:
                self.parent_window.repository.delete_interaction(interaction_id)
            self.status_label.setText(f"状态：已删除 {count} 条")
            self.refresh()
            return
        record = self.current_record()
        if not record:
            return
        interaction_id = int(record["id"])
        if QMessageBox.question(self, "确认删除", f"确认删除录制数据 #{interaction_id}？") == QMessageBox.Yes:
            self.parent_window.repository.delete_interaction(interaction_id)
            self.status_label.setText("状态：删除成功")
            self.refresh()

    def execute_sql(self) -> None:
        try:
            columns, rows, affected = self.parent_window.repository.execute_sql(self.sql_editor.toPlainText())
            if columns:
                lines = [" | ".join(columns)]
                lines.extend(" | ".join(str(value) for value in row) for row in rows[:200])
                if len(rows) > 200:
                    lines.append(f"... 仅显示前 200 行，共 {len(rows)} 行")
                self.sql_result.setPlainText("\n".join(lines))
            else:
                self.sql_result.setPlainText(f"执行完成，影响行数：{affected}")
                self.refresh()
            self.status_label.setText("状态：SQL 执行完成")
        except Exception as exc:
            self.sql_result.setPlainText(f"执行失败：{exc}")
            self.status_label.setText("状态：SQL 执行失败")

    def update_action_states(self) -> None:
        has_selection = self.current_record() is not None
        checked_ids = self.checked_record_ids() if hasattr(self, "table") else []
        has_checked = bool(checked_ids)
        for button in [self.edit_button, self.save_button, self.detail_button]:
            button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection or has_checked)
        self.delete_button.setText(f"删除已选({len(checked_ids)})" if has_checked else "删除")
        limit = self.page_size.value() if hasattr(self, "page_size") else 100
        max_page = max(1, (self.total + limit - 1) // limit)
        if hasattr(self, "prev_button"):
            self.prev_button.setEnabled(self.page > 1)
            self.next_button.setEnabled(self.page < max_page)

    def _edit_dialog(self, initial: dict, title: str) -> dict | None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QFormLayout(dialog)
        inputs = {}
        for key, label in self.EDIT_FIELDS:
            field = QLineEdit(str(initial.get(key) or ""))
            inputs[key] = field
            layout.addRow(label, field)
        buttons = QHBoxLayout()
        save = self._button("保存", "primary")
        cancel = self._button("取消", "secondary")
        save.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addRow(buttons)
        dialog.resize(680, 620)
        if dialog.exec() != QDialog.Accepted:
            return None
        data = {key: field.text().strip() for key, field in inputs.items()}
        for int_key in ["call_index", "success"]:
            if data.get(int_key):
                data[int_key] = int(data[int_key])
        data.setdefault("profile_name", "default")
        data.setdefault("test_item_code", "DEFAULT_TEST")
        data.setdefault("variant_name", "normal")
        return data

    def _card(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return frame

    def _card_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("CardTitle")
        return label

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    def _button(self, text: str, kind: str) -> QPushButton:
        button = QPushButton(text)
        name = {
            "primary": "PrimaryButton",
            "secondary": "SecondaryButton",
            "danger": "DangerButton",
        }[kind]
        button.setObjectName(name)
        return button

    def _apply_table_columns(self) -> None:
        widths = {
            "_selected": 58,
            "product_name": 82,
            "process_station": 96,
            "product_code": 100,
            "tu_name": 120,
            "instrument_alias": 92,
            "call_index": 76,
            "success": 60,
        }
        for col, (key, _) in enumerate(self.COLUMNS):
            if key in ("request_text", "response_text"):
                self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
            else:
                self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
                self.table.setColumnWidth(col, widths.get(key, 100))
