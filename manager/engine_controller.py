"""Manage the bundled Byparr engine process on Windows."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
from api_diagnostics import format_api_diagnostic
from PySide6.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    QStandardPaths,
    QThread,
    QTimer,
    Signal,
)


def is_routine_api_probe_log_line(line: str) -> bool:
    """Identify successful health-poll access lines that add no diagnostic value."""
    text = str(line).rstrip()
    return '"GET /openapi.json HTTP/' in text and text.endswith("200 OK")


class ApiHealthCheckWorker(QThread):
    """Probe the local Byparr API without blocking the Manager interface."""

    result = Signal(object, int)

    def __init__(self, port: int, parent=None):
        super().__init__(parent)
        self.port = port

    def run(self) -> None:
        started = time.perf_counter()
        status_code = None
        try:
            response = httpx.get(
                f"http://127.0.0.1:{self.port}/openapi.json",
                timeout=0.8,
                follow_redirects=False,
                trust_env=False,
            )
            status_code = response.status_code
        except httpx.RequestError:
            pass
        elapsed = round((time.perf_counter() - started) * 1000)
        self.result.emit(status_code, elapsed)


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
        self._api_ready_logged = False
        self._stop_timeout_timer = QTimer(self)
        self._stop_timeout_timer.setSingleShot(True)
        self._stop_timeout_timer.setInterval(12_000)
        self._stop_timeout_timer.timeout.connect(self._force_stop_if_needed)

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.started.connect(self._on_started)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)

        self.health_timer = QTimer(self)
        self.health_timer.setInterval(1500)
        self.health_timer.timeout.connect(self._check_health)
        self._health_worker = None

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
        self._api_ready_logged = False
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
        self._stop_timeout_timer.start()

    def restart(self) -> None:
        if not self.is_running:
            self.start()
            return
        self._restart_after_stop = True
        self._set_status("Restarting")
        self.log_message.emit("Restart requested.")
        self.process.terminate()
        self._stop_timeout_timer.start()

    def _force_stop_if_needed(self) -> None:
        if self.is_running:
            self.log_message.emit("Engine did not stop cleanly within 12 seconds; forcing shutdown.")
            self.process.kill()

    def _on_started(self) -> None:
        self.log_message.emit("Byparr engine process started; waiting for API readiness.")
        self.health_timer.start()
        self._check_health()

    def _check_health(self) -> None:
        if not self.is_running:
            self.health_timer.stop()
            return
        if self._health_worker is not None and self._health_worker.isRunning():
            return
        worker = ApiHealthCheckWorker(self.port, self)
        self._health_worker = worker
        worker.result.connect(self._on_health_result)
        worker.finished.connect(
            lambda current=worker: self._on_health_worker_finished(current)
        )
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _on_health_worker_finished(self, worker) -> None:
        if self._health_worker is worker:
            self._health_worker = None

    def _on_health_result(self, status_code, elapsed: int) -> None:
        # A late probe must never mark an already-stopped engine as Running.
        if not self.is_running:
            return
        if status_code == 200:
            self._set_status("Running")
            if not self._api_ready_logged:
                self.log_message.emit(format_api_diagnostic(
                    "Byparr startup API", True, status_code,
                    elapsed, "OpenAPI endpoint ready",
                ))
                self._api_ready_logged = True
            # Startup needs rapid retries; steady-state monitoring does not.
            self.health_timer.setInterval(30_000)
            if not self.health_timer.isActive():
                self.health_timer.start()
        elif self._api_ready_logged:
            self._set_status("API unavailable")
            self.health_timer.setInterval(10_000)
            if not self.health_timer.isActive():
                self.health_timer.start()
        else:
            self._set_status("Starting")

    def _read_output(self) -> None:
        output = bytes(self.process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        for line in output.splitlines():
            if line.strip():
                self.log_message.emit(line.rstrip())

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._stop_timeout_timer.stop()
        self.health_timer.stop()
        self._read_output()
        if exit_status == QProcess.NormalExit and exit_code == 0:
            self.log_message.emit("Byparr engine stopped.")
        else:
            self.log_message.emit(f"Byparr engine exited (code {exit_code}).")
        should_restart = self._restart_after_stop
        self._restart_after_stop = False
        self._api_ready_logged = False
        self._set_status("Stopped")
        if should_restart:
            QTimer.singleShot(500, self.start)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.FailedToStart:
            self._stop_timeout_timer.stop()
            self.health_timer.stop()
            self.log_message.emit("Windows could not start the bundled Byparr engine.")
            self._set_status("Failed to start")

    def shutdown(self) -> None:
        """Stop background probes and the child process before the Manager exits."""
        self._restart_after_stop = False
        self._stop_timeout_timer.stop()
        self.health_timer.stop()
        if self._health_worker is not None and self._health_worker.isRunning():
            # The probe has a sub-second network timeout; wait so Qt never
            # destroys a controller while its child QThread is still running.
            self._health_worker.wait(1000)
        self._health_worker = None
        if self.is_running:
            self.process.terminate()
            if not self.process.waitForFinished(2500):
                self.process.kill()
                self.process.waitForFinished(1500)
