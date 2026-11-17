import ipaddress
import re
import sys

import httpx

from PySide6.QtCore import QSettings, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

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


class ByparrManager(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Byparr Manager")
        self.resize(1180, 760)
        self.setMinimumSize(980, 650)
        self.settings = QSettings("RedHeX", "ByparrManager")
        self.secret_store = SecretStore()
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
        version = QLabel("BY PARR MANAGER  •  v0.4")
        version.setObjectName("version")
        side.addWidget(version)

        self.pages.addWidget(self.create_dashboard())
        self.pages.addWidget(self.create_integrations())
        self.pages.addWidget(self.create_settings())
        self.pages.addWidget(self.create_logs())

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
            "Engine", "Not connected", "Service controls are coming next"
        ))
        metrics.addWidget(self.make_metric(
            "API port", "8191", "Default local API endpoint"
        ))
        metrics.addWidget(self.make_metric(
            "Integrations", "2 planned", "Prowlarr and Jackett"
        ))
        layout.addLayout(metrics)

        panel, panel_layout = self.make_panel(
            "Service connection",
            "Check whether the Byparr API is responding on this computer."
        )

        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #e7bd70; font-size: 18px;")
        status_row.addWidget(self.status_dot, 0, Qt.AlignVCenter)

        self.api_status = QLabel("Not checked")
        self.api_status.setObjectName("status_value")
        status_row.addWidget(self.api_status)
        status_row.addStretch()
        panel_layout.addLayout(status_row)

        self.endpoint_label = QLabel(
            f"LOCAL API     {api_endpoint(self.api_host, self.api_port)}"
        )
        self.endpoint_label.setObjectName("muted")
        panel_layout.addWidget(self.endpoint_label)

        controls = QHBoxLayout()
        controls.setSpacing(10)

        self.check_button = QPushButton("Check API connection")
        self.check_button.setObjectName("primary")
        self.check_button.setCursor(Qt.PointingHandCursor)
        self.check_button.clicked.connect(self.check_api_connection)
        controls.addWidget(self.check_button)

        for label in ("Start service", "Stop service", "Restart service"):
            button = QPushButton(label)
            button.setEnabled(False)
            button.setToolTip(
                "Windows service controls have not been implemented yet."
            )
            controls.addWidget(button)

        controls.addStretch()
        panel_layout.addLayout(controls)
        layout.addWidget(panel)

        info_panel, info_layout = self.make_panel(
            "Welcome to Byparr Manager",
            "The management interface is running. The next development stage "
            "will connect the official Byparr engine and add Windows service "
            "installation, startup and control features."
        )
        info_label = QLabel("Your existing API connection check is available above.")
        info_label.setObjectName("muted")
        info_layout.addWidget(info_label)
        layout.addWidget(info_panel)
        layout.addStretch()
        return page

    def check_api_connection(self):
        if hasattr(self, "api_worker") and self.api_worker.isRunning():
            return

        self.api_status.setText("Checking connection...")
        self.status_dot.setStyleSheet("color: #e7bd70; font-size: 18px;")
        self.check_button.setEnabled(False)

        self.api_worker = ApiCheckWorker(api_endpoint(self.api_host, self.api_port), self)
        self.api_worker.result.connect(self.handle_api_check_result)
        self.api_worker.finished.connect(
            lambda: self.check_button.setEnabled(True)
        )
        self.api_worker.start()

    def handle_api_check_result(self, success, message):
        self.api_status.setText(message)
        color = "#48c78e" if success else "#e57373"
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 18px;")

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
            "Live service logging will be connected during the Windows service setup."
        )
        log_view = QTextEdit()
        log_view.setReadOnly(True)
        log_view.setPlainText(
            "Byparr Manager started.\n"
            "Interface version: 0.4\n"
            "Waiting for service logging..."
        )
        panel_layout.addWidget(log_view)
        layout.addWidget(panel)
        layout.addStretch()
        return page


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ByparrManager()
    window.show()
    sys.exit(app.exec())