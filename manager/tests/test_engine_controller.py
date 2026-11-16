from pathlib import Path

from engine_controller import EngineController


def test_engine_paths_are_relative_to_application_root(tmp_path: Path):
    controller = EngineController(application_root=tmp_path)

    assert controller.executable_path == (
        tmp_path / "engine" / "ByparrEngine" / "ByparrEngine.exe"
    )
    assert controller.browser_cache_path == tmp_path / "engine" / "browser-cache"


def test_missing_engine_is_reported(qtbot, tmp_path: Path):
    controller = EngineController(application_root=tmp_path)

    with qtbot.waitSignal(controller.status_changed, timeout=1000) as signal:
        assert controller.start() is False

    assert signal.args == ["Engine files missing"]
