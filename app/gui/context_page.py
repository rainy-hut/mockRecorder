from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class ContextPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent_window = parent
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
        save = QPushButton("保存")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self.save)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(save)
        card_layout.addLayout(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(6)
        self.product = QLineEdit()
        self.process_station = QLineEdit()
        self.product_code = QLineEdit()
        for col, (label_text, widget) in enumerate([
            ("产品", self.product),
            ("工序工位", self.process_station),
            ("编码", self.product_code),
        ]):
            label = QLabel(label_text)
            label.setObjectName("FieldLabel")
            grid.addWidget(label, 0, col)
            grid.addWidget(widget, 1, col)
        card_layout.addLayout(grid)
        layout.addWidget(card)

    def load_values(self, config) -> None:
        self.product.setText(config.currentProduct)
        self.process_station.setText(config.currentProcessStation)
        self.product_code.setText(config.currentProductCode)

    def load_runtime_context(self, snapshot: dict[str, str]) -> None:
        self.product.setText(snapshot["product_name"])
        self.process_station.setText(snapshot["process_station"])
        self.product_code.setText(snapshot["product_code"])

    def save(self) -> None:
        self.parent_window.save_context(
            self.product.text().strip() or "MM",
            self.process_station.text().strip() or "FT1-MP1",
            self.product_code.text().strip() or "03020001",
        )
