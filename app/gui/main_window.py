import logging
import sys

from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QListWidget, QMainWindow, QMessageBox, QStackedWidget, QHBoxLayout, QVBoxLayout, QWidget

from app.config.config_manager import ConfigManager
from app.constants import DISPLAY_NAME
from app.db.database import Database
from app.db.repository import Repository
from app.gui.dashboard_page import DashboardPage
from app.gui.log_page import LogPage
from app.gui.record_browser_page import RecordBrowserPage
from app.gui.setup_page import SetupPage
from app.paths import get_config_path, get_database_path, resource_path
from app.proxy.context_control_server import ContextControlServer
from app.proxy.proxy_manager import ProxyManager
from app.proxy.replay_engine import ReplayEngine
from app.recorder.async_writer import AsyncWriter
from app.recorder.recorder_service import RecorderService
from app.recorder.runtime_context import RuntimeContext
from app.utils.log_utils import configure_logging

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        app_icon = load_app_icon()
        self.setWindowIcon(app_icon)
        if QApplication.instance():
            QApplication.instance().setWindowIcon(app_icon)
        self.log_path = configure_logging()
        self.config_manager = ConfigManager(get_config_path())
        self.app_config = self.config_manager.load()
        self.database = Database(get_database_path(self.app_config.databasePath))
        self.repository = Repository(self.database)
        self.repository.init_schema()
        self.runtime_context = RuntimeContext(
            self.app_config.mode,
            self.app_config.currentProfile,
            self.app_config.currentTestItemCode,
            self.app_config.currentVariant,
            self.app_config.currentProduct,
            self.app_config.currentProcessStation,
            self.app_config.currentProductCode,
            self.app_config.currentTuName,
        )
        self.writer = AsyncWriter(self.repository)
        self.writer.start()
        self.recorder_service = RecorderService(self.writer)
        self.replay_engine = ReplayEngine(self.repository, self.runtime_context, self.app_config.appendNewLineWhenReplay)
        self.proxy_manager = ProxyManager(self.app_config, self.runtime_context, self.recorder_service, self.replay_engine)
        self.context_control_server = ContextControlServer(
            self.app_config.controlHost,
            self.app_config.controlPort,
            self.runtime_context,
            self._context_notice_received,
        )
        for instrument in self.app_config.instruments:
            self.repository.save_instrument_config(instrument)
        self.repository.upsert_profile(self.app_config.currentProfile)
        self.repository.upsert_test_item(self.app_config.currentTestItemCode)
        self._build_ui()
        self.refresh_all()
        logger.debug("Application started")

    def _build_ui(self) -> None:
        self.setWindowTitle(DISPLAY_NAME)
        self.resize(1280, 800)
        self.setMinimumSize(960, 560)
        workspace = QWidget()
        layout = QHBoxLayout(workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 18, 16, 16)
        sidebar_layout.setSpacing(14)
        app_title = QLabel("录制回放平台")
        app_title.setObjectName("SidebarTitle")
        sidebar_layout.addWidget(app_title)
        self.nav = QListWidget()
        self.stack = QStackedWidget()
        self.setup_page = SetupPage(self)
        self.dashboard_page = DashboardPage(self)
        self.record_page = RecordBrowserPage(self)
        self.log_page = LogPage(self.log_path)
        pages = [
            ("运行控制", self.dashboard_page),
            ("基础配置", self.setup_page),
            ("数据查询", self.record_page),
            ("日志", self.log_page),
        ]
        for title, page in pages:
            self.nav.addItem(title)
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        sidebar_layout.addWidget(self.nav, 1)
        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(workspace)

    def center_on_screen(self) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if not screen:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())

    def refresh_all(self) -> None:
        self.setup_page.load(self.app_config)
        self.record_page.refresh()
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        snapshot = self.runtime_context.snapshot()
        self.dashboard_page.refresh({
            "mode": snapshot["mode"],
            "proxy": "运行中" if self.proxy_manager.is_running() else "已停止",
            "control": f"{self.app_config.controlHost}:{self.app_config.controlPort} " + ("运行中" if self.context_control_server.is_running() else "已停止"),
            "database": str(self.database.path),
            "scene": f"{snapshot['product_name']} / {snapshot['process_station']} / {snapshot['product_code']}",
            "tu_name": snapshot["tu_name"],
            "instrument_count": len(self.app_config.instruments),
            "interaction_count": self.repository.count_interactions(),
        })

    def start_proxy(self) -> None:
        warnings = self.proxy_manager.start()
        self.context_control_server.stop()
        self.context_control_server = ContextControlServer(
            self.app_config.controlHost,
            self.app_config.controlPort,
            self.runtime_context,
            self._context_notice_received,
        )
        self.context_control_server.start()
        if warnings:
            QMessageBox.warning(self, "代理启动提示", "\n".join(warnings))
        self.refresh_dashboard()

    def stop_proxy(self) -> None:
        self.proxy_manager.stop()
        self.context_control_server.stop()
        self.refresh_dashboard()

    def choose_mode(self, mode: str) -> None:
        self.set_mode(mode)
        self.nav.setCurrentRow(0)

    def enter_business_mode(self, mode: str) -> None:
        self.set_mode(mode)
        self.nav.setCurrentRow(0)

    def show_records(self) -> None:
        self.nav.setCurrentRow(2)

    def show_entry(self) -> None:
        self.nav.setCurrentRow(0)

    def set_mode(self, mode: str) -> None:
        self.app_config.mode = mode
        self.runtime_context.set_mode(mode)
        self.config_manager.save(self.app_config)
        logger.debug("Mode changed to %s", mode)
        self.refresh_dashboard()

    def reset_replay_counter(self) -> None:
        self.runtime_context.reset_replay_counter()
        logger.debug("Replay counters reset")

    def save_context(
        self,
        product_name: str,
        process_station: str,
        product_code: str,
        tu_name: str,
    ) -> None:
        self.app_config.currentProduct = product_name
        self.app_config.currentProcessStation = process_station
        self.app_config.currentProductCode = product_code
        self.app_config.currentTuName = tu_name
        self.runtime_context.set_scene(product_name, process_station, product_code)
        self.runtime_context.set_current_tu_name(tu_name)
        self.config_manager.save(self.app_config)
        self.setup_page.load(self.app_config)
        self.refresh_dashboard()

    def save_instruments(self, instruments) -> None:
        self.app_config.instruments = instruments
        for instrument in instruments:
            self.repository.save_instrument_config(instrument)
        self.config_manager.save(self.app_config)
        self.refresh_dashboard()
        QMessageBox.information(self, "已保存", "仪器配置已保存")

    def import_config(self, path: str) -> None:
        self.app_config = self.config_manager.import_json(path)
        self.proxy_manager.stop()
        self.runtime_context.set_mode(self.app_config.mode)
        self.runtime_context.set_current_profile(self.app_config.currentProfile)
        self.runtime_context.set_current_test_item(self.app_config.currentTestItemCode)
        self.runtime_context.set_current_variant(self.app_config.currentVariant)
        self.runtime_context.set_scene(
            self.app_config.currentProduct,
            self.app_config.currentProcessStation,
            self.app_config.currentProductCode,
        )
        self.runtime_context.set_current_tu_name(self.app_config.currentTuName)
        self.refresh_all()

    def export_config(self, path: str) -> None:
        self.config_manager.export_json(path, self.app_config)
        QMessageBox.information(self, "导出完成", path)

    def closeEvent(self, event) -> None:
        self.proxy_manager.stop()
        self.context_control_server.stop()
        self.writer.stop()
        event.accept()

    def _context_notice_received(self, notice: dict[str, str]) -> None:
        snapshot = self.runtime_context.snapshot()
        self.app_config.currentProduct = snapshot["product_name"]
        self.app_config.currentProcessStation = snapshot["process_station"]
        self.app_config.currentProductCode = snapshot["product_code"]
        self.app_config.currentTuName = snapshot["tu_name"]
        logger.debug("Runtime context updated by notice: %s", notice)


def run_app() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(load_app_icon())
    app.setStyleSheet(_app_stylesheet())
    window = MainWindow()
    window.show()
    window.center_on_screen()
    sys.exit(app.exec())


def load_app_icon() -> QIcon:
    return QIcon(str(resource_path("app/assets/app_icon.svg")))


def _app_stylesheet() -> str:
    return """
    QWidget {
        background: #F6F8FB;
        color: #172033;
        font-size: 13px;
        font-family: "Inter", "Segoe UI", "PingFang SC", "Microsoft YaHei";
    }
    QFrame#Sidebar {
        background: #111827;
        border: 0;
    }
    QLabel#SidebarTitle {
        background: transparent;
        color: #FFFFFF;
        font-size: 17px;
        font-weight: 800;
        padding: 4px 4px 10px 4px;
    }
    QListWidget {
        background: transparent;
        color: #CBD5E1;
        border: 0;
        padding: 0;
    }
    QListWidget::item {
        min-height: 36px;
        padding: 8px 12px;
        border-radius: 6px;
        color: #9CA3AF;
    }
    QListWidget::item:hover {
        background: #1F2937;
        color: #E5E7EB;
    }
    QListWidget::item:selected {
        background: #2563EB;
        color: white;
    }
    QPushButton {
        background: #2563EB;
        color: white;
        border: 0;
        border-radius: 6px;
        min-height: 36px;
        padding: 8px 14px;
        font-weight: 600;
    }
    QPushButton:hover { background: #1D4ED8; }
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
    QPushButton:disabled {
        background: #F3F4F6;
        color: #9CA3AF;
        border: 1px solid #E5E7EB;
    }
    QLineEdit, QSpinBox {
        background: white;
        border: 1px solid #CBD5E1;
        border-radius: 5px;
        padding: 6px 8px;
    }
    QTableWidget {
        background: white;
        alternate-background-color: #F8FAFC;
        gridline-color: #E2E8F0;
        selection-background-color: #DBEAFE;
        selection-color: #111827;
        border: 1px solid #E2E8F0;
    }
    QHeaderView::section {
        background: #EEF2F7;
        color: #334155;
        padding: 7px;
        border: 0;
        border-right: 1px solid #E2E8F0;
        font-weight: 600;
    }
    QGroupBox {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        margin-top: 18px;
        padding: 14px;
        font-weight: 700;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px;
    }
    QLabel#HeroTitle {
        font-size: 28px;
        font-weight: 800;
        color: #0F172A;
    }
    QLabel#CardTitle {
        font-size: 18px;
        font-weight: 800;
        color: #0F172A;
    }
    QLabel#SubtleText {
        color: #64748B;
    }
    QFrame#ModeCard {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        min-height: 132px;
    }
    QFrame#ActiveModeCard {
        background: #EFF6FF;
        border: 1px solid #2563EB;
        border-radius: 8px;
        min-height: 132px;
    }
    QLabel#ModeBadge {
        background: #2563EB;
        color: white;
        border-radius: 9px;
        padding: 2px 8px;
        font-size: 12px;
        font-weight: 700;
    }
    QFrame#Panel {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
    }
    QLabel#FieldName {
        color: #64748B;
        font-weight: 600;
    }
    QTextEdit {
        border: 1px solid #E2E8F0;
        border-radius: 6px;
    }
    """
