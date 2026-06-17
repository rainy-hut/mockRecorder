from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class ContextPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent_window = parent
        self.loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("ConfigCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("测试场景配置")
        title.setObjectName("ConfigCardTitle")
        self.status = QLabel("已保存")
        self.status.setObjectName("SavedBadge")
        save = QPushButton("保存")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self.save)
        header.addWidget(title)
        header.addWidget(self.status)
        header.addStretch(1)
        header.addWidget(save)
        card_layout.addLayout(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(6)
        self.product = QLineEdit()
        self.process_station = QLineEdit()
        self.product_code = QLineEdit()
        self.tu_name = QLineEdit()
        for index, (label_text, widget) in enumerate([
            ("产品", self.product),
            ("工序工位", self.process_station),
            ("编码", self.product_code),
            ("测试项", self.tu_name),
        ]):
            row = (index // 2) * 2
            col = index % 2
            label = QLabel(label_text)
            label.setObjectName("FieldLabel")
            grid.addWidget(label, row, col)
            grid.addWidget(widget, row + 1, col)
        card_layout.addLayout(grid)
        layout.addWidget(card)
        for widget in [self.product, self.process_station, self.product_code, self.tu_name]:
            widget.textChanged.connect(lambda _text: self.set_dirty(True))

    def load_values(self, config) -> None:
        self.loading = True
        self.product.setText(config.currentProduct)
        self.process_station.setText(config.currentProcessStation)
        self.product_code.setText(config.currentProductCode)
        self.tu_name.setText(config.currentTuName)
        self.loading = False
        self.set_dirty(False)

    def load_runtime_context(self, snapshot: dict[str, str]) -> None:
        self.loading = True
        self.product.setText(snapshot["product_name"])
        self.process_station.setText(snapshot["process_station"])
        self.product_code.setText(snapshot["product_code"])
        self.tu_name.setText(snapshot["tu_name"])
        self.loading = False
        self.set_dirty(False)

    def save(self) -> None:
        self.parent_window.save_context(
            self.product.text().strip() or "MM",
            self.process_station.text().strip() or "FT1-MP1",
            self.product_code.text().strip() or "03020001",
            self.tu_name.text().strip() or "UNSET",
        )
        self.set_dirty(False)
        self.status.setText("保存成功")
        QTimer.singleShot(1500, lambda: self.status.setText("已保存"))

    def set_dirty(self, dirty: bool) -> None:
        if self.loading:
            return
        self.status.setText("有未保存修改" if dirty else "已保存")
        self.status.setObjectName("DirtyBadge" if dirty else "SavedBadge")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
