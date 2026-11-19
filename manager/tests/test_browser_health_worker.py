import httpx

from main import BrowserHealthCheckWorker


def test_browser_health_worker_reports_success(monkeypatch, qtbot):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, timeout, **kwargs: httpx.Response(
            200,
            json={
                "msg": "Byparr is working!",
                "version": "unknown",
                "userAgent": "test-agent",
            },
        ),
    )
    worker = BrowserHealthCheckWorker("http://127.0.0.1:8191")

    with qtbot.waitSignal(worker.result, timeout=1000) as blocker:
        worker.run()

    assert blocker.args == [True, "Healthy (version unknown)"]


def test_browser_health_worker_reports_timeout(monkeypatch, qtbot):
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("health check timed out")

    monkeypatch.setattr(httpx, "get", timeout)
    worker = BrowserHealthCheckWorker("http://127.0.0.1:8191")

    with qtbot.waitSignal(worker.result, timeout=1000) as blocker:
        worker.run()

    assert blocker.args == [
        False,
        "Health check timed out. The API may still be available.",
    ]


def test_browser_health_worker_reports_http_error(monkeypatch, qtbot):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, timeout, **kwargs: httpx.Response(503, request=httpx.Request("GET", url)),
    )
    worker = BrowserHealthCheckWorker("http://127.0.0.1:8191")

    with qtbot.waitSignal(worker.result, timeout=1000) as blocker:
        worker.run()

    assert blocker.args == [False, "Health check returned HTTP 503"]
