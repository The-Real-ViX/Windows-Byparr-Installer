import httpx

from prowlarr_check import ProwlarrIntegrationCheckWorker


def response(status, payload, url="http://127.0.0.1:9696/api/v1/downloadclient"):
    return httpx.Response(
        status,
        json=payload,
        request=httpx.Request("GET", url),
    )


def run_worker(monkeypatch, clients, test_status=200, test_results=None):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response(200, clients))
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: response(
            test_status,
            test_results if test_results is not None else [],
            "http://127.0.0.1:9696/api/v1/downloadclient/testall",
        ),
    )
    worker = ProwlarrIntegrationCheckWorker("http://127.0.0.1:9696", "test-api-key")
    captured = []
    worker.result.connect(lambda *values: captured.append(values))
    worker.run()
    return captured[0]


def test_reports_qbittorrent_connection_success(monkeypatch):
    result = run_worker(
        monkeypatch,
        [{
            "id": 7,
            "name": "qBittorrent",
            "implementation": "QBittorrent",
            "enable": True,
        }],
        test_results=[{"id": 7, "validationFailures": []}],
    )
    assert result == (True, "Connected", True, "Connection test passed")


def test_reports_qbittorrent_not_configured(monkeypatch):
    result = run_worker(monkeypatch, [])
    assert result == (True, "Connected", False, "Not configured in Prowlarr")


def test_reports_qbittorrent_disabled(monkeypatch):
    result = run_worker(
        monkeypatch,
        [{
            "id": 7,
            "name": "qBittorrent",
            "implementation": "QBittorrent",
            "enable": False,
        }],
    )
    assert result == (True, "Connected", False, "Configured but disabled")


def test_reports_qbittorrent_test_failure(monkeypatch):
    result = run_worker(
        monkeypatch,
        [{
            "id": 7,
            "name": "qBittorrent",
            "implementation": "QBittorrent",
            "enable": True,
        }],
        test_status=400,
        test_results=[{
            "id": 7,
            "validationFailures": [{"errorMessage": "Connection refused"}],
        }],
    )
    assert result == (
        True,
        "Connected",
        False,
        "Connection test failed — check Prowlarr",
    )


def test_reports_missing_api_key():
    worker = ProwlarrIntegrationCheckWorker("http://127.0.0.1:9696", "")
    captured = []
    worker.result.connect(lambda *values: captured.append(values))
    worker.run()
    assert captured[0] == (False, "API key not saved", False, "Not checked")


def test_prowlarr_requests_disable_redirects_and_environment_proxies(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs)
        return response(200, [])

    monkeypatch.setattr(httpx, "get", fake_get)
    worker = ProwlarrIntegrationCheckWorker("http://127.0.0.1:9696", "key")
    worker.run()
    assert calls[0]["follow_redirects"] is False
    assert calls[0]["trust_env"] is False


def test_prowlarr_worker_emits_status_and_duration_diagnostic(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response(200, []))
    worker = ProwlarrIntegrationCheckWorker("http://127.0.0.1:9696", "key")
    captured = []
    worker.diagnostic.connect(lambda *values: captured.append(values))
    worker.run()
    assert captured[0][0] == "Prowlarr"
    assert captured[0][1] is True
    assert captured[0][2] == 200
    assert captured[0][3] >= 0
