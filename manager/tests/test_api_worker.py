import httpx

from main import ApiCheckWorker


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_api_worker_reports_healthy_endpoint(qtbot, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: FakeResponse(200))
    worker = ApiCheckWorker()

    with qtbot.waitSignal(worker.result, timeout=2000) as signal:
        worker.start()

    assert signal.args == [True, "API responding"]


def test_api_worker_reports_unavailable_endpoint(qtbot, monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", raise_connection_error)
    worker = ApiCheckWorker()

    with qtbot.waitSignal(worker.result, timeout=2000) as signal:
        worker.start()

    assert signal.args == [False, "API not responding"]
