from pathlib import Path

from PySide6.QtCore import QProcess, QStandardPaths

from engine_controller import EngineController, is_routine_api_probe_log_line


def test_engine_executable_is_relative_to_application_root(tmp_path: Path):
    controller = EngineController(application_root=tmp_path)

    assert controller.executable_path == (
        tmp_path / "engine" / "ByparrEngine" / "ByparrEngine.exe"
    )


def test_browser_engine_is_bundled_with_application(tmp_path: Path):
    controller = EngineController(application_root=tmp_path)

    assert controller.browser_engine_path == tmp_path / "engine" / "browser-engine"


def test_browser_cache_uses_user_writable_app_data():
    controller = EngineController()
    cache = controller.browser_cache_path

    expected_app_data = Path(
        QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    )
    assert cache.name == "browser-cache"
    assert cache.is_absolute()
    assert cache.parent == expected_app_data
    assert not cache.is_relative_to(
        controller.application_root / "engine"
    )


def test_missing_engine_is_reported(qtbot, tmp_path: Path):
    controller = EngineController(application_root=tmp_path)

    with qtbot.waitSignal(controller.status_changed, timeout=1000) as signal:
        assert controller.start() is False

    assert signal.args == ["Engine files missing"]


def test_successful_openapi_health_poll_log_is_filtered():
    assert is_routine_api_probe_log_line(
        'INFO: 127.0.0.1:50000 - "GET /openapi.json HTTP/1.1" 200 OK'
    )


def test_failed_openapi_request_log_is_preserved():
    assert not is_routine_api_probe_log_line(
        'INFO: 127.0.0.1:50000 - "GET /openapi.json HTTP/1.1" 500 Internal Server Error'
    )


def test_engine_stop_timeout_is_cancellable(qtbot):
    controller = EngineController()
    assert controller._stop_timeout_timer.isSingleShot()
    assert controller._stop_timeout_timer.interval() == 12_000
    controller._stop_timeout_timer.start()
    assert controller._stop_timeout_timer.isActive()

    controller._on_finished(0, QProcess.NormalExit)

    assert not controller._stop_timeout_timer.isActive()

def test_engine_health_polling_slows_after_api_is_ready(monkeypatch):
    controller = EngineController()
    monkeypatch.setattr(EngineController, "is_running", property(lambda _self: True))

    assert controller.health_timer.interval() == 1500
    controller._on_health_result(200, 12)

    assert controller._status == "Running"
    assert controller._api_ready_logged is True
    assert controller.health_timer.interval() == 30_000
    assert controller.health_timer.isActive()

    controller._on_health_result(None, 800)
    assert controller._status == "API unavailable"
    assert controller.health_timer.interval() == 10_000

    controller._on_health_result(200, 15)
    assert controller._status == "Running"
    assert controller.health_timer.interval() == 30_000
