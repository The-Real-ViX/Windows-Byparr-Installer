from pathlib import Path

from engine_controller import EngineController


def test_engine_executable_is_relative_to_application_root(tmp_path: Path):
    controller = EngineController(application_root=tmp_path)

    assert controller.executable_path == (
        tmp_path / "engine" / "ByparrEngine" / "ByparrEngine.exe"
    )


def test_browser_cache_uses_user_writable_app_data():
    controller = EngineController()
    cache = controller.browser_cache_path

    assert cache.name == "browser-cache"
    assert "ByparrManager" in str(cache)
    assert cache != controller.application_root / "engine" / "browser-cache"


def test_missing_engine_is_reported(qtbot, tmp_path: Path):
    controller = EngineController(application_root=tmp_path)

    with qtbot.waitSignal(controller.status_changed, timeout=1000) as signal:
        assert controller.start() is False

    assert signal.args == ["Engine files missing"]
