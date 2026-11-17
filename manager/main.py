"""Cross-platform desktop entry point for Byparr Manager."""

import ipaddress
import re
import secrets
import shutil
import sys
from datetime import datetime
from pathlib import Path

import httpx
from PySide6.QtCore import QSettings, QStandardPaths, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from build_info import APP_VERSION, BUILD_NUMBER
from engine_controller import EngineController
from secret_store import SecretStorageError, SecretStore


DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8191


def validate_api_settings(host, port):
    """Validate a host name/IP address and a TCP port without accepting a URL."""
    host = host.strip()
    if not host or any(char in host for char in "/\\?#@") or any(
        char.isspace() for char in host
    ):
        raise ValueError("Enter a host name or IP address only, without http:// or a path.")

    try:
        ipaddress.ip_address(host)
    except ValueError:
        if len(host) > 253 or not re.fullmatch(
            r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host
        ):
            raise ValueError("Enter a valid host name or IP address.")
        if any(not label or len(label) > 63 for label in host.split(".")):
            raise ValueError("Enter a valid host name or IP address.")

    try:
        port_number = int(port)
    except (TypeError, ValueError) as error:
        raise ValueError("Port must be a number between 1 and 65535.") from error
    if not 1 <= port_number <= 65535:
        raise ValueError("Port must be between 1 and 65535.")

    return host, port_number


def api_endpoint(host, port):
    """Build an HTTP endpoint, including brackets around IPv6 literals."""
    host, port = validate_api_settings(host, port)
    if ":" in host:
        host = f"[{host}]"
    return f"http://{host}:{port}"


class ApiCheckWorker(QThread):
    """Check the local Byparr API without blocking the desktop interface."""

    result = Signal(bool, str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            response = httpx.get(
                f"{self.url}/openapi.json",
                timeout=3.0,
            )
            if response.status_code == 200:
                self.result.emit(True, "API responding")
            else:
                self.result.emit(
                    False,
                    f"Unexpected response: HTTP {response.status_code}",
                )
        except httpx.RequestError:
            self.result.emit(False, "API not responding")


class BrowserHealthCheckWorker(QThread):
    """Run Byparr's browser-backed health check without freezing the interface."""

    result = Signal(bool, str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            # Upstream /health launches a browser and navigates to Google.
            # Allow more than its usual 60-second navigation timeout.
            response = httpx.get(f"{self.url}/health", timeout=75.0)
            if response.status_code != 200:
                self.result.emit(
                    False,
                    f"Health check returned HTTP {response.status_code}",
                )
                return

            payload = response.json()
            if payload.get("msg") == "Byparr is working!":
                version = payload.get("version") or "unknown"
                self.result.emit(True, f"Healthy (version {version})")
            else:
                self.result.emit(False, "Unexpected health-check response")
        except httpx.TimeoutException:
            self.result.emit(
                False,
                "Health check timed out. The API may still be available.",
            )
        except (httpx.RequestError, ValueError):
            self.result.emit(False, "Browser health check could not be completed.")


class ByparrManager(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Byparr Manager")
        self.resize(1180, 760)
        self.setMinimumSize(980, 650)
        self.settings = QSettings("RedHeX", "ByparrManager")
        self.secret_store = SecretStore()
        self.engine_controller = EngineController(self)
        self.engine_controller.status_changed.connect(self.handle_engine_status)
        self.engine_controller.log_message.connect(self.append_log)
        self.api_host = self.settings.value("api/host", DEFAULT_API_HOST, type=str)
        self.api_port = self.settings.value("api/port", DEFAULT_API_PORT, type=int)
        try:
            self.api_host, self.api_port = validate_api_settings(
                self.api_host, self.api_port
            )
        except ValueError:
            self.api_host, self.api_port = DEFAULT_API_HOST, DEFAULT_API_PORT

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #10141c;
                color: #edf2fb;
                font-family: "Arial";
                font-size: 13px;
            }
            QFrame#sidebar {
                background: #151b26;
                border-right: 1px solid #273142;
            }
            QLabel#brand {
                color: #8daaff;
                font-size: 23px;
                font-weight: 800;
                letter-spacing: 1px;
            }
            QLabel#brand_subtitle {
                color: #8793a7;
                font-size: 11px;
            }
            QLabel#version {
                color: #718096;
                font-size: 11px;
            }
            QLabel#eyebrow {
                color: #8daaff;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel#page_title {
                color: #f4f7fc;
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#page_subtitle {
                color: #9aa7ba;
                font-size: 13px;
            }
            QLabel#panel_title {
                color: #f1f5fb;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#muted {
                color: #98a5b8;
            }
            QLabel#status_value {
                font-size: 27px;
                font-weight: 700;
                color: #e7bd70;
            }
            QLabel#metric_value {
                color: #f3f6fc;
                font-size: 22px;
                font-weight: 700;
            }
            QFrame#panel, QFrame#metric {
                background: #1a2230;
                border: 1px solid #2b3749;
                border-radius: 12px;
            }
            QFrame#status_accent {
                background: #4169e1;
                border: none;
                border-radius: 2px;
            }
            QPushButton#danger {
                background: #8f3942;
                border: 1px solid #ad4a55;
                color: #ffffff;
                padding: 9px 15px;
                border-radius: 6px;
                font-weight: 700;
            }
            QPushButton#danger:hover {
                background: #a94752;
            }
            QPushButton#danger:pressed {
                background: #743039;
            }
            QPushButton {
                background: #273244;
                color: #e8eef8;
                border: 1px solid #35445b;
                border-radius: 8px;
                padding: 10px 15px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background: #33425a;
                border-color: #526887;
            }
            QPushButton:pressed {
                background: #202b3c;
            }
            QPushButton:disabled {
                color: #687589;
                background: #202936;
                border-color: #293445;
            }
            QPushButton#primary {
                background: #4169e1;
                color: white;
                border: 1px solid #5279ed;
            }
            QPushButton#primary:hover {
                background: #5279ef;
            }
            QPushButton#primary:disabled {
                color: #8794a8;
                background: #2b3545;
                border: 1px solid #39475b;
            }
            QPushButton#nav {
                background: transparent;
                color: #aab6c8;
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 12px 14px;
                text-align: left;
                font-weight: 600;
            }
            QPushButton#nav:hover {
                background: #202b3b;
                color: #f3f6fc;
            }
            QPushButton#nav:checked {
                background: #263a62;
                color: #ffffff;
                border: 1px solid #38558b;
            }
            QLineEdit, QTextEdit {
                background: #131a25;
                color: #e8eef8;
                border: 1px solid #35445b;
                border-radius: 8px;
                padding: 10px;
                selection-background-color: #4169e1;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #6688ed;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(235)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 26, 18, 20)
        side.setSpacing(7)

        brand = QLabel("BYPARR")
        brand.setObjectName("brand")
        side.addWidget(brand)

        brand_subtitle = QLabel("MANAGER  •  WINDOWS EDITION")
        brand_subtitle.setObjectName("brand_subtitle")
        side.addWidget(brand_subtitle)
        side.addSpacing(34)

        nav_caption = QLabel("WORKSPACE")
        nav_caption.setObjectName("eyebrow")
        side.addWidget(nav_caption)
        side.addSpacing(8)

        self.pages = QStackedWidget()
        self.nav_buttons = []

        for label, symbol, index in [
            ("Dashboard", "▦", 0),
            ("Integrations", "⇄", 1),
            ("Settings", "⚙", 2),
            ("Logs", "≡", 3),
            ("Info / Credits", "ⓘ", 4),
        ]:
            button = QPushButton(f"  {symbol}     {label}")
            button.setObjectName("nav")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(
                lambda checked=False, page=index: self.change_page(page)
            )
            side.addWidget(button)
            self.nav_buttons.append(button)

        side.addStretch()
        version = QLabel(f"VERSION {APP_VERSION}  •  BUILD {BUILD_NUMBER}")
        version.setObjectName("version")
        side.addWidget(version)

        self.pages.addWidget(self.create_dashboard())
        self.pages.addWidget(self.create_integrations())
        self.pages.addWidget(self.create_settings())
        self.pages.addWidget(self.create_logs())
        self.pages.addWidget(self.create_info())

        root.addWidget(sidebar)
        root.addWidget(self.pages, 1)
        self.change_page(0)

    def change_page(self, index):
        self.pages.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def page_header(self, eyebrow, title, subtitle):
        wrapper = QVBoxLayout()
        wrapper.setSpacing(7)
        small = QLabel(eyebrow.upper())
        small.setObjectName("eyebrow")
        heading = QLabel(title)
        heading.setObjectName("page_title")
        description = QLabel(subtitle)
        description.setObjectName("page_subtitle")
        description.setWordWrap(True)
        wrapper.addWidget(small)
        wrapper.addWidget(heading)
        wrapper.addWidget(description)
        wrapper.addSpacing(12)
        return wrapper

    def make_panel(self, title, description=""):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        heading = QLabel(title)
        heading.setObjectName("panel_title")
        layout.addWidget(heading)

        if description:
            detail = QLabel(description)
            detail.setObjectName("muted")
            detail.setWordWrap(True)
            layout.addWidget(detail)

        return panel, layout

    def make_metric(self, title, value, note):
        panel = QFrame()
        panel.setObjectName("metric")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(7)

        caption = QLabel(title.upper())
        caption.setObjectName("eyebrow")
        number = QLabel(value)
        number.setObjectName("metric_value")
        if title == "Engine":
            self.engine_metric_value = number
        detail = QLabel(note)
        detail.setObjectName("muted")
        detail.setWordWrap(True)

        layout.addWidget(caption)
        layout.addWidget(number)
        layout.addWidget(detail)
        return panel

    def create_dashboard(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(38, 32, 38, 30)
        layout.setSpacing(18)
        layout.addLayout(self.page_header(
            "Overview", "Dashboard",
            "Monitor your Byparr installation and manage its connections."
        ))

        metrics = QHBoxLayout()
        metrics.setSpacing(14)
        metrics.addWidget(self.make_metric(
            "Engine", "Stopped", "Bundled Windows engine"
        ))
        metrics.addWidget(self.make_metric(
            "API port", "8191", "Default local API endpoint"
        ))
        integration_metric = self.make_metric(
            "API keys", "Checking...", "Saved integration credentials"
        )
        metrics.addWidget(integration_metric)
        self.integration_metric_value = integration_metric.findChild(
            QLabel, "metric_value"
        )
        self.integration_metric_note = integration_metric.findChildren(
            QLabel, "muted"
        )[-1]
        self.update_integration_metric()
        layout.addLayout(metrics)

        panel, panel_layout = self.make_panel(
            "Service connection",
            "Start and manage the bundled Byparr engine on this computer."
        )

        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #e7bd70; font-size: 18px;")
        status_row.addWidget(self.status_dot, 0, Qt.AlignVCenter)

        self.engine_status = QLabel("Stopped")
        self.engine_status.setObjectName("status_value")
        status_row.addWidget(self.engine_status)
        status_row.addStretch()
        panel_layout.addLayout(status_row)

        self.endpoint_label = QLabel(
            f"LOCAL API     {api_endpoint(self.api_host, self.api_port)}"
        )
        self.endpoint_label.setObjectName("muted")
        panel_layout.addWidget(self.endpoint_label)

        api_row = QHBoxLayout()
        api_row.addWidget(QLabel("API connection"))
        self.api_connection_status = QLabel("Not checked")
        self.api_connection_status.setObjectName("muted")
        api_row.addWidget(self.api_connection_status)
        api_row.addStretch()
        panel_layout.addLayout(api_row)

        browser_row = QHBoxLayout()
        browser_row.addWidget(QLabel("Browser health"))
        self.browser_health_status = QLabel("Not checked")
        self.browser_health_status.setObjectName("muted")
        browser_row.addWidget(self.browser_health_status)
        browser_row.addStretch()
        panel_layout.addLayout(browser_row)

        controls = QVBoxLayout()
        controls.setSpacing(10)

        api_controls = QHBoxLayout()
        api_controls.setSpacing(10)

        self.check_button = QPushButton("Check API")
        self.check_button.setObjectName("primary")
        self.check_button.setToolTip("Check the Byparr API connection")
        self.check_button.setMinimumWidth(140)
        self.check_button.setCursor(Qt.PointingHandCursor)
        self.check_button.clicked.connect(self.check_api_connection)
        api_controls.addWidget(self.check_button)

        self.browser_health_button = QPushButton("Browser Health")
        self.browser_health_button.setObjectName("primary")
        self.browser_health_button.setToolTip("Run the browser-backed Byparr health check (may take up to 75 seconds)")
        self.browser_health_button.setMinimumWidth(160)
        self.browser_health_button.setEnabled(False)
        self.browser_health_button.setCursor(Qt.PointingHandCursor)
        self.browser_health_button.clicked.connect(self.check_browser_health)
        api_controls.addWidget(self.browser_health_button)
        api_controls.addStretch()
        controls.addLayout(api_controls)

        engine_controls = QHBoxLayout()
        engine_controls.setSpacing(10)

        self.start_button = QPushButton("Start engine")
        self.start_button.setObjectName("primary")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.start_engine)
        engine_controls.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop engine")
        self.stop_button.setEnabled(False)
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setObjectName("primary")
        self.stop_button.clicked.connect(self.stop_engine)
        engine_controls.addWidget(self.stop_button)

        self.restart_button = QPushButton("Restart engine")
        self.restart_button.setEnabled(False)
        self.restart_button.setCursor(Qt.PointingHandCursor)
        self.restart_button.setObjectName("primary")
        self.restart_button.clicked.connect(self.restart_engine)
        engine_controls.addWidget(self.restart_button)

        engine_controls.addStretch()

        self.exit_button = QPushButton("Exit Application")
        self.exit_button.setCursor(Qt.PointingHandCursor)
        self.exit_button.setObjectName("danger")
        self.exit_button.clicked.connect(self.request_exit)
        engine_controls.addWidget(self.exit_button)

        controls.addLayout(engine_controls)
        panel_layout.addLayout(controls)
        layout.addWidget(panel)

        info_panel, info_layout = self.make_panel(
            "Welcome to Byparr Manager",
            "The Manager controls the bundled Byparr engine. Start it above, "
            "then use the API check to confirm that its local endpoint responds."
        )
        info_label = QLabel("The engine runs locally and does not depend on Brave or Chrome.")
        info_label.setObjectName("muted")
        info_layout.addWidget(info_label)
        layout.addWidget(info_panel)
        layout.addStretch()
        return page

    def start_engine(self):
        self.engine_controller.port = self.api_port
        self.engine_controller.start()

    def stop_engine(self):
        self.engine_controller.stop()

    def restart_engine(self):
        self.engine_controller.port = self.api_port
        self.engine_controller.restart()

    def handle_engine_status(self, status):
        self.engine_status.setText(status)
        if hasattr(self, "engine_metric_value"):
            self.engine_metric_value.setText(status)
        colors = {
            "Running": "#48c78e",
            "Stopped": "#98a5b8",
            "Starting": "#e7bd70",
            "Stopping": "#e7bd70",
            "Restarting": "#e7bd70",
            "Engine files missing": "#e57373",
            "Failed to start": "#e57373",
        }
        self.status_dot.setStyleSheet(
            f"color: {colors.get(status, '#e7bd70')}; font-size: 18px;"
        )
        self.start_button.setEnabled(status in {
            "Stopped", "Engine files missing", "Failed to start"
        })
        self.stop_button.setEnabled(status in {"Starting", "Running", "Restarting"})
        self.restart_button.setEnabled(status in {"Starting", "Running"})
        if status in {"Stopped", "Engine files missing", "Failed to start"}:
            self.browser_health_status.setText("Not checked")
            self.browser_health_status.setStyleSheet("color: #98a5b8;")
            self.browser_health_button.setEnabled(False)
        else:
            self.browser_health_button.setEnabled(status == "Running")

    def append_log(self, message):
        if hasattr(self, "log_view"):
            self.log_view.append(message)

    def request_exit(self):
        answer = QMessageBox.question(
            self,
            "Exit Byparr Manager",
            "Exit the application and stop the Byparr engine?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.close()

    def closeEvent(self, event):
        self.engine_controller.shutdown()
        event.accept()

    def check_api_connection(self):
        if hasattr(self, "api_worker") and self.api_worker.isRunning():
            return

        self.api_connection_status.setText("Checking...")
        self.api_connection_status.setStyleSheet("color: #e7bd70;")
        self.check_button.setEnabled(False)

        self.api_worker = ApiCheckWorker(api_endpoint(self.api_host, self.api_port), self)
        self.api_worker.result.connect(self.handle_api_check_result)
        self.api_worker.finished.connect(
            lambda: self.check_button.setEnabled(True)
        )
        self.api_worker.start()

    def handle_api_check_result(self, success, message):
        self.api_connection_status.setText(message)
        color = "#48c78e" if success else "#e57373"
        self.api_connection_status.setStyleSheet(f"color: {color};")

    def check_browser_health(self):
        if self.engine_controller._status != "Running":
            self.browser_health_status.setText("Start the engine first")
            self.browser_health_status.setStyleSheet("color: #e7bd70;")
            return
        if hasattr(self, "browser_health_worker") and self.browser_health_worker.isRunning():
            return

        self.browser_health_status.setText(
            "Checking browser... this can take up to 75 seconds"
        )
        self.browser_health_status.setStyleSheet("color: #e7bd70;")
        self.browser_health_button.setEnabled(False)
        self.browser_health_worker = BrowserHealthCheckWorker(
            api_endpoint(self.api_host, self.api_port), self
        )
        self.browser_health_worker.result.connect(
            self.handle_browser_health_result
        )
        self.browser_health_worker.finished.connect(
            lambda: self.browser_health_button.setEnabled(
                self.engine_controller._status == "Running"
            )
        )
        self.browser_health_worker.start()

    def handle_browser_health_result(self, success, message):
        self.browser_health_status.setText(message)
        color = "#48c78e" if success else "#e57373"
        self.browser_health_status.setStyleSheet(f"color: {color};")
        self.append_log(f"Browser health check: {message}")

    def update_integration_metric(self):
        """Show saved credentials, without implying the services are connected."""
        saved = []
        for integration_id, name in (("prowlarr", "Prowlarr"), ("jackett", "Jackett")):
            try:
                if self.secret_store.get(integration_id):
                    saved.append(name)
            except SecretStorageError:
                continue

        count = len(saved)
        self.integration_metric_value.setText(
            "None saved" if count == 0 else f"{count} saved"
        )
        self.integration_metric_note.setText(
            "No API keys stored"
            if count == 0
            else f"{', '.join(saved)} API key{'s' if count > 1 else ''} stored securely"
        )

    def create_integrations(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(38, 32, 38, 30)
        layout.setSpacing(18)
        layout.addLayout(self.page_header(
            "Connections", "Integrations",
            "Save API keys in your computer's credential vault. Keys are never "
            "written to the Manager settings file."
        ))

        self.add_integration_panel(
            layout,
            "Prowlarr",
            "prowlarr",
            "Configure the API key used to connect to your Prowlarr instance."
        )
        self.add_integration_panel(
            layout,
            "Jackett",
            "jackett",
            "Configure the API key used to connect to your Jackett instance."
        )

        layout.addStretch()
        return page

    def add_integration_panel(self, parent_layout, name, integration_id, description):
        panel, panel_layout = self.make_panel(name, description)

        status = QLabel()
        status.setObjectName("muted")
        status.setWordWrap(True)
        try:
            saved_secret = self.secret_store.get(integration_id)
            status.setText(
                "API key saved in the operating-system credential vault."
                if saved_secret
                else "No API key saved."
            )
        except SecretStorageError as error:
            status.setText(str(error))
        panel_layout.addWidget(status)

        key_input = QLineEdit()
        key_input.setEchoMode(QLineEdit.Password)
        key_input.setPlaceholderText("Enter API key")
        key_input.setClearButtonEnabled(True)
        panel_layout.addWidget(key_input)

        actions = QHBoxLayout()
        save_button = QPushButton("Save API key securely")
        save_button.setObjectName("primary")
        save_button.setCursor(Qt.PointingHandCursor)

        def save_secret():
            try:
                self.secret_store.set(integration_id, key_input.text())
            except (SecretStorageError, ValueError) as error:
                status.setText(str(error))
                status.setStyleSheet("color: #e57373;")
                return
            key_input.clear()
            status.setText("API key saved in the operating-system credential vault.")
            status.setStyleSheet("color: #48c78e;")
            self.update_integration_metric()

        save_button.clicked.connect(save_secret)
        actions.addWidget(save_button)

        remove_button = QPushButton("Remove saved key")
        remove_button.setCursor(Qt.PointingHandCursor)

        def remove_secret():
            try:
                self.secret_store.delete(integration_id)
            except SecretStorageError as error:
                status.setText(str(error))
                status.setStyleSheet("color: #e57373;")
                return
            key_input.clear()
            status.setText("Saved API key removed from the credential vault.")
            status.setStyleSheet("color: #98a5b8;")
            self.update_integration_metric()

        remove_button.clicked.connect(remove_secret)
        actions.addWidget(remove_button)
        actions.addStretch()
        panel_layout.addLayout(actions)
        parent_layout.addWidget(panel)

    def create_settings(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(38, 32, 38, 30)
        layout.setSpacing(18)
        layout.addLayout(self.page_header(
            "Configuration", "Settings",
            "Configure the local Byparr API connection. Settings are saved on this computer."
        ))

        panel, panel_layout = self.make_panel(
            "API configuration",
            "The default is localhost on port 8191. Keep the API bound to your own "
            "computer unless you have deliberately configured a trusted network."
        )

        panel_layout.addWidget(QLabel("API host or IP address"))
        self.api_host_input = QLineEdit(self.api_host)
        self.api_host_input.setPlaceholderText("127.0.0.1")
        panel_layout.addWidget(self.api_host_input)

        panel_layout.addWidget(QLabel("API port"))
        self.api_port_input = QLineEdit(str(self.api_port))
        self.api_port_input.setPlaceholderText("8191")
        panel_layout.addWidget(self.api_port_input)

        actions = QHBoxLayout()
        save_button = QPushButton("Save settings")
        save_button.setObjectName("primary")
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.clicked.connect(self.save_api_settings)
        actions.addWidget(save_button)

        reset_button = QPushButton("Restore defaults")
        reset_button.setCursor(Qt.PointingHandCursor)
        reset_button.clicked.connect(self.reset_api_settings)
        actions.addWidget(reset_button)
        actions.addStretch()
        panel_layout.addLayout(actions)

        self.settings_status = QLabel("Settings are stored locally on this computer.")
        self.settings_status.setObjectName("muted")
        self.settings_status.setWordWrap(True)
        panel_layout.addWidget(self.settings_status)

        layout.addWidget(panel)
        layout.addStretch()
        return page

    def save_api_settings(self):
        try:
            host, port = validate_api_settings(
                self.api_host_input.text(), self.api_port_input.text()
            )
        except ValueError as error:
            self.settings_status.setText(str(error))
            self.settings_status.setStyleSheet("color: #e57373;")
            return

        self.api_host = host
        self.api_port = port
        self.engine_controller.port = port
        self.settings.setValue("api/host", host)
        self.settings.setValue("api/port", port)
        self.settings.sync()
        self.endpoint_label.setText(
            f"LOCAL API     {api_endpoint(self.api_host, self.api_port)}"
        )
        self.settings_status.setText(
            "Settings saved. The next API check will use this address."
        )
        self.settings_status.setStyleSheet("color: #48c78e;")

    def reset_api_settings(self):
        self.api_host_input.setText(DEFAULT_API_HOST)
        self.api_port_input.setText(str(DEFAULT_API_PORT))
        self.save_api_settings()

    def export_logs(self):
        """Save the currently available Manager and engine log output as UTF-8 text."""
        exported_at = datetime.now().astimezone().isoformat(timespec="seconds")
        suggested_name = datetime.now().strftime("ByparrManager-logs-%Y%m%d-%H%M%S.txt")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Byparr Manager logs",
            suggested_name,
            "Text files (*.txt);;All files (*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".txt"):
            file_path += ".txt"

        header = (
            "Byparr Manager log export\n"
            f"Exported: {exported_at}\n"
            "Interface version: 0.4\n"
            f"API endpoint: {api_endpoint(self.api_host, self.api_port)}\n"
            + "=" * 72
            + "\n\n"
        )
        try:
            with open(file_path, "w", encoding="utf-8", newline="\n") as log_file:
                log_file.write(header)
                log_file.write(self.log_view.toPlainText())
                log_file.write("\n")
        except OSError as error:
            QMessageBox.warning(
                self,
                "Could not export logs",
                f"The log file could not be saved:\n{error}",
            )
            return

        QMessageBox.information(
            self,
            "Logs exported",
            f"Your logs were saved successfully to:\n{file_path}",
        )

    def create_info(self):
        """Show application identity, upstream attribution, licences, and project links."""
        page = QWidget()
        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(38, 32, 38, 30)
        outer_layout.setSpacing(18)
        outer_layout.addLayout(self.page_header(
            "About this application", "Info / Credits",
            "Project details, acknowledgements, licence information and useful links."
        ))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(14)

        about_panel, about_layout = self.make_panel(
            "Byparr Manager",
            "An independent Windows 11 installer and desktop management interface "
            "for the Byparr browser-challenge solving engine."
        )
        about_text = QLabel(
            "<b>Application version:</b> 0.4.0<br>"
            "<b>Maintained by:</b> RedHeX<br>"
            "<b>Project credits:</b> RedHeX &amp; The TinMan"
        )
        about_text.setTextFormat(Qt.RichText)
        about_text.setWordWrap(True)
        about_text.setObjectName("muted")
        about_layout.addWidget(about_text)
        layout.addWidget(about_panel)

        upstream_panel, upstream_layout = self.make_panel(
            "Original Byparr project",
            "The bundled browser engine is the original Byparr project, not software "
            "written by the Manager project."
        )
        upstream_text = QLabel(
            "Created and maintained by <b>ThePhaseless</b>.<br>"
            "The source revision bundled by this build is pinned in the project "
            "file UPSTREAM.lock.json."
        )
        upstream_text.setObjectName("muted")
        upstream_text.setWordWrap(True)
        upstream_layout.addWidget(upstream_text)
        upstream_link = QLabel(
            '<a href="https://github.com/ThePhaseless/Byparr">'
            "Open the original Byparr project on GitHub</a>"
        )
        upstream_link.setOpenExternalLinks(True)
        upstream_layout.addWidget(upstream_link)
        layout.addWidget(upstream_panel)

        links_panel, links_layout = self.make_panel(
            "Project links",
            "Find the source code, project information and the original engine."
        )
        for label, url in [
            ("Byparr Manager source repository",
             "https://github.com/The-Real-ViX/Windows-Byparr-Installer"),
            ("Project README and documentation",
             "https://github.com/The-Real-ViX/Windows-Byparr-Installer#readme"),
            ("Original Byparr engine",
             "https://github.com/ThePhaseless/Byparr"),
            ("GNU General Public License v3",
             "https://www.gnu.org/licenses/gpl-3.0.html"),
        ]:
            link = QLabel(f'<a href="{url}">{label}</a>')
            link.setOpenExternalLinks(True)
            links_layout.addWidget(link)
        layout.addWidget(links_panel)

        licence_panel, licence_layout = self.make_panel(
            "Licences and acknowledgements",
            "The original Byparr engine is distributed under the GNU General Public "
            "License, version 3 (GPL-3.0). The complete licence text and third-party "
            "notices are supplied as separate files with the application."
        )
        licence_text = QLabel(
            "Please retain the original authors' copyright and licence notices. "
            "Other bundled components have their own licence terms; consult "
            "THIRD_PARTY_NOTICES.md for the component and redistribution information "
            "provided with this build."
        )
        licence_text.setObjectName("muted")
        licence_text.setWordWrap(True)
        licence_layout.addWidget(licence_text)
        layout.addWidget(licence_panel)

        disclaimer_panel, disclaimer_layout = self.make_panel(
            "Independent project and warranty notice",
            "Byparr Manager is an independent community project. It is not affiliated "
            "with, endorsed by, or an official release of ThePhaseless or the original "
            "Byparr project. The Byparr name and upstream work remain attributed to "
            "their respective authors."
        )
        disclaimer_text = QLabel(
            "This application is provided without warranty, to the extent permitted "
            "by applicable law. See the included GPL-3.0 licence and third-party "
            "notices for the terms that apply to the bundled software."
        )
        disclaimer_text.setObjectName("muted")
        disclaimer_text.setWordWrap(True)
        disclaimer_layout.addWidget(disclaimer_text)
        layout.addWidget(disclaimer_panel)

        layout.addStretch()
        scroll.setWidget(content)
        outer_layout.addWidget(scroll, 1)
        return page

    def create_logs(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(38, 32, 38, 30)
        layout.setSpacing(18)
        layout.addLayout(self.page_header(
            "Diagnostics", "Logs",
            "Review application and service activity."
        ))

        panel, panel_layout = self.make_panel(
            "Application activity",
            "Live output from the bundled Byparr engine appears here."
        )
        actions = QHBoxLayout()
        export_button = QPushButton("Export logs")
        export_button.setObjectName("primary")
        export_button.setCursor(Qt.PointingHandCursor)
        export_button.clicked.connect(self.export_logs)
        actions.addWidget(export_button)
        actions.addStretch()
        panel_layout.addLayout(actions)

        log_view = QTextEdit()
        self.log_view = log_view
        log_view.setReadOnly(True)
        log_view.setMinimumHeight(360)
        log_view.setPlainText(
            "Byparr Manager started.\n"
            "Interface version: 0.4\n"
            "Waiting for engine activity..."
        )
        panel_layout.addWidget(log_view, 1)
        layout.addWidget(panel, 1)
        return page


def run_credential_smoke_test():
    """Exercise the packaged OS credential vault without exposing the test secret."""
    store = SecretStore()
    integration = f"ci-smoke-{secrets.token_hex(8)}"
    expected = secrets.token_urlsafe(32)
    try:
        store.set(integration, expected)
        actual = store.get(integration)
        if actual != expected:
            raise RuntimeError("Credential vault read-back did not match the saved value.")
        store.delete(integration)
        if store.get(integration) is not None:
            raise RuntimeError("Credential vault entry still exists after deletion.")
        print("Credential vault round-trip passed.")
        return 0
    except (SecretStorageError, RuntimeError) as error:
        try:
            store.delete(integration)
        except SecretStorageError as cleanup_error:
            print(f"Credential test cleanup warning: {cleanup_error}", file=sys.stderr)
        print(f"Credential vault smoke test failed: {error}", file=sys.stderr)
        return 1


def run_full_uninstall_cleanup():
    """Remove Byparr Manager user data and integration credentials on request."""
    try:
        store = SecretStore()
        for integration in ("prowlarr", "jackett"):
            store.delete(integration)

        settings = QSettings("RedHeX", "ByparrManager")
        settings.clear()
        settings.sync()
        if settings.status() != QSettings.NoError:
            raise RuntimeError("Could not clear application settings.")

        # Match EngineController.browser_cache_path and avoid other RedHeX data.
        app_data = QStandardPaths.writableLocation(
            QStandardPaths.AppLocalDataLocation
        )
        if not app_data:
            app_data = str(
                Path.home() / "AppData" / "Local" / "RedHeX" / "ByparrManager"
            )
        data_directory = Path(app_data)
        if data_directory.exists():
            shutil.rmtree(data_directory)

        print("Full uninstall cleanup completed.")
        return 0
    except (SecretStorageError, OSError, RuntimeError):
        # Never print credential values or backend exception details.
        print(
            "Full uninstall cleanup could not remove all user data. "
            "Some settings, cache, or saved credentials may remain.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    if "--credential-smoke-test" in sys.argv:
        sys.exit(run_credential_smoke_test())
    if "--full-uninstall-cleanup" in sys.argv:
        sys.exit(run_full_uninstall_cleanup())
    app = QApplication(sys.argv)
    window = ByparrManager()
    window.show()
    sys.exit(app.exec())