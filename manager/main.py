import sys
import httpx

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QLineEdit,
    QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal


class ApiCheckWorker(QThread):
    """Check the local Byparr API without blocking the desktop interface."""

    result = Signal(bool, str)

    def run(self):
        try:
            response = httpx.get(
                "http://127.0.0.1:8191/openapi.json",
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

        endpoint = QLabel("LOCAL API     http://127.0.0.1:8191")
        endpoint.setObjectName("muted")
        panel_layout.addWidget(endpoint)

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

        self.api_worker = ApiCheckWorker(self)
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
            "Connect the indexer applications that work with your setup."
        ))

        for name, description, state in [
            ("Prowlarr", "Configure the Prowlarr address and API key.", "NOT CONFIGURED"),
            ("Jackett", "Configure the Jackett address and API key.", "NOT CONFIGURED"),
        ]:
            panel, panel_layout = self.make_panel(name, description)
            state_label = QLabel(state)
            state_label.setObjectName("eyebrow")
            panel_layout.addWidget(state_label)
            layout.addWidget(panel)

        layout.addStretch()
        return page

    def create_settings(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(38, 32, 38, 30)
        layout.setSpacing(18)
        layout.addLayout(self.page_header(
            "Configuration", "Settings",
            "Review the current local API connection details."
        ))

        panel, panel_layout = self.make_panel(
            "API configuration",
            "These are the current default connection details. Editing and saving "
            "settings will be added in a later stage."
        )

        panel_layout.addWidget(QLabel("API address"))
        address = QLineEdit("127.0.0.1")
        address.setReadOnly(True)
        panel_layout.addWidget(address)

        panel_layout.addWidget(QLabel("API port"))
        port = QLineEdit("8191")
        port.setReadOnly(True)
        panel_layout.addWidget(port)

        layout.addWidget(panel)
        layout.addStretch()
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