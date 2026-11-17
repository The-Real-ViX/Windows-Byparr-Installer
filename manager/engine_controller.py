"""Manage the bundled Byparr engine process on Windows."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
from PySide6.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    QStandardPaths,
    QTimer,
    Signal,
)


class EngineController(QObject):
    """Start, monitor, stop, and restart the bundled Byparr engine."""

    status_changed = Signal(str)
    log_message = Signal(str)

    def __init__(self, parent=None, application_root: Path | None = None):
        super().__init__(parent)
        self.application_root = (
            Path(application_root) if application_root else self._application_root()
        )
        self.port = 8191
        self._status = "Stopped"
        self._restart_after_stop = False

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.started.connect(self._on_started)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)

        self.health_timer = QTimer(self)
        self.health_timer.setInterval(1500)
        self.health_timer.timeout.connect(self._check_health)

    @staticmethod
    def _application_root() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent.parent

    @property
    def executable_path(self) -> Path:
        return self.application_root / "engine" / "ByparrEngine" / "ByparrEngine.exe"

    @property
    def browser_engine_path(self) -> Path:
        """Return the read-only patched browser engine bundled with the application."""
        return self.application_root / "engine" / "browser-engine"

    @property
    def browser_cache_path(self) -> Path:
        """Return a per-user cache directory that is writable after installation."""
        app_data = QStandardPaths.writableLocation(
            QStandardPaths.AppLocalDataLocation
        )
        if not app_data:
            app_data = str(Path.home() / "AppData" / "Local" / "RedHeX" / "ByparrManager")
        return Path(app_data) / "browser-cache"

    @property
    def is_running(self) -> bool:
        return self.process.state() != QProcess.NotRunning

    def _set_status(self, status: str) -> None:
        if status != self._status:
            self._status = status
            self.status_changed.emit(status)

    def start(self) -> bool:
        if self.is_running:
            return True

        executable = self.executable_path
        if not executable.is_file():
            message = f"Bundled engine not found: {executable}"
            self.log_message.emit(message)
            self._set_status("Engine files missing")
            return False

        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("HOST", "127.0.0.1")
        environment.insert("PORT", str(self.port))
        environment.insert("INVISIBLE_PLAYWRIGHT_ENGINE_DIR", str(self.browser_engine_path))
        environment.insert("INVISIBLE_PLAYWRIGHT_CACHE_DIR", str(self.browser_cache_path))
        environment.insert("BROWSER_LOCALE", "en-GB")
        self.process.setProcessEnvironment(environment)
        self.process.setWorkingDirectory(str(executable.parent))
        self._restart_after_stop = False
        self._set_status("Starting")
        self.log_message.emit("Starting the bundled Byparr engine...")
        self.process.start(str(executable), [])
        return True

    def stop(self) -> None:
        self._restart_after_stop = False
        if not self.is_running:
            self._set_status("Stopped")
            return
        self._set_status("Stopping")
        self.log_message.emit("Stopping the Byparr engine...")
        self.process.terminate()
        QTimer.singleShot(4000, self._force_stop_if_needed)

    def restart(self) -> None:
        if not self.is_running:
            self.start()
            return
        self._restart_after_stop = True
        self._set_status("Restarting")
        self.log_message.emit("Restart requested.")
        self.process.terminate()
        QTimer.singleShot(4000, self._force_stop_if_needed)

    def _force_stop_if_needed(self) -> None:
        if self.is_running:
            self.log_message.emit("Engine did not stop cleanly; forcing shutdown.")
            self.process.kill()

    def _on_started(self) -> None:
        self.log_message.emit("Byparr engine process started; waiting for API readiness.")
        self.health_timer.start()
        self._check_health()

    def _check_health(self) -> None:
        if not self.is_running:
            self.health_timer.stop()
            return
        try:
            response = httpx.get(
                f"http://127.0.0.1:{self.port}/openapi.json",
                timeout=0.4,
            )
            if response.status_code == 200:
                self._set_status("Running")
            elif self._status != "Starting":
                self._set_status("Starting")
        except httpx.RequestError:
            if self._status == "Running":
                self._set_status("Starting")

    def _read_output(self) -> None:
        output = bytes(self.process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        for line in output.splitlines():
            if line.strip():
                self.log_message.emit(line.rstrip())

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self.health_timer.stop()
        self._read_output()
        if exit_status == QProcess.NormalExit and exit_code == 0:
            self.log_message.emit("Byparr engine stopped.")
        else:
            self.log_message.emit(f"Byparr engine exited (code {exit_code}).")
        should_restart = self._restart_after_stop
        self._restart_after_stop = False
        self._set_status("Stopped")
        if should_restart:
            QTimer.singleShot(500, self.start)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.FailedToStart:
            self.health_timer.stop()
            self.log_message.emit("Windows could not start the bundled Byparr engine.")
            self._set_status("Failed to start")

    def shutdown(self) -> None:
        """Stop the child process before the Manager exits."""
        self._restart_after_stop = False
        self.health_timer.stop()
        if self.is_running:
            self.process.terminate()
            if not self.process.waitForFinished(2500):
                self.process.kill()
                self.process.waitForFinished(1500)
