import httpx

from main import ApiCheckWorker, api_endpoint, validate_api_settings


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_api_worker_reports_healthy_endpoint(qtbot, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: FakeResponse(200))
    worker = ApiCheckWorker("http://127.0.0.1:8191")

    with qtbot.waitSignal(worker.result, timeout=2000) as signal:
        worker.start()

    assert worker.wait(2000)
    assert signal.args == [True, "API responding"]


def test_api_worker_reports_unavailable_endpoint(qtbot, monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", raise_connection_error)
    worker = ApiCheckWorker()

    with qtbot.waitSignal(worker.result, timeout=2000) as signal:
        worker.start()

    assert worker.wait(2000)
    assert signal.args == [False, "API not responding"]



def test_api_settings_accept_valid_host_and_port():
    assert validate_api_settings("localhost", "8191") == ("localhost", 8191)
    assert api_endpoint("127.0.0.1", 8191) == "http://127.0.0.1:8191"
    assert api_endpoint("::1", 8191) == "http://[::1]:8191"


def test_api_settings_reject_invalid_host_or_port():
    import pytest

    for host, port in [
        ("", "8191"),
        ("http://localhost", "8191"),
        ("localhost/path", "8191"),
        ("localhost", "0"),
        ("localhost", "65536"),
        ("localhost", "not-a-number"),
    ]:
        with pytest.raises(ValueError):
            validate_api_settings(host, port)
