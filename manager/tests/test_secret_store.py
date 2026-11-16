import pytest

import secret_store
from secret_store import SERVICE_NAME, SecretStorageError, SecretStore


class NativeTestBackend:
    __module__ = "keyring.backends.macOS"


class UnsupportedTestBackend:
    __module__ = "keyring.backends.fail"


def test_secret_store_uses_keyring_for_credentials(monkeypatch):
    saved = {}
    monkeypatch.setattr(secret_store.keyring, "get_keyring", lambda: NativeTestBackend())
    monkeypatch.setattr(
        secret_store.keyring,
        "set_password",
        lambda service, username, password: saved.update(
            {(service, username): password}
        ),
    )
    monkeypatch.setattr(
        secret_store.keyring,
        "get_password",
        lambda service, username: saved.get((service, username)),
    )
    monkeypatch.setattr(
        secret_store.keyring,
        "delete_password",
        lambda service, username: saved.pop((service, username)),
    )

    store = SecretStore()
    store.set("prowlarr", "test-secret")
    assert saved[(SERVICE_NAME, "prowlarr")] == "test-secret"
    assert store.get("prowlarr") == "test-secret"
    store.delete("prowlarr")
    assert store.get("prowlarr") is None


def test_secret_store_refuses_unsupported_backend(monkeypatch):
    monkeypatch.setattr(
        secret_store.keyring, "get_keyring", lambda: UnsupportedTestBackend()
    )
    store = SecretStore()

    with pytest.raises(SecretStorageError, match="No supported"):
        store.set("jackett", "must-not-be-saved")


def test_secret_store_rejects_empty_secret(monkeypatch):
    monkeypatch.setattr(secret_store.keyring, "get_keyring", lambda: NativeTestBackend())
    with pytest.raises(ValueError, match="cannot be empty"):
        SecretStore().set("prowlarr", "")
