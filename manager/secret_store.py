"""Secure storage for integration credentials using native OS keyrings."""

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

SERVICE_NAME = "RedHeX.ByparrManager"
SUPPORTED_BACKENDS = (
    "keyring.backends.macOS",
    "keyring.backends.Windows",
    "keyring.backends.SecretService",
    "keyring.backends.kwallet",
)


class SecretStorageError(RuntimeError):
    """Raised when a supported operating-system credential store is unavailable."""


class SecretStore:
    """Store integration API keys in the native credential manager, never QSettings."""

    def _backend(self):
        try:
            backend = keyring.get_keyring()
        except Exception as error:
            raise SecretStorageError(
                "The operating-system credential store is unavailable."
            ) from error

        module = type(backend).__module__
        if not any(module.startswith(prefix) for prefix in SUPPORTED_BACKENDS):
            raise SecretStorageError(
                "No supported operating-system credential store is available. "
                "No key was saved; install or enable the system keychain/credential vault."
            )
        return backend

    def get(self, integration):
        self._backend()
        try:
            return keyring.get_password(SERVICE_NAME, integration)
        except Exception as error:
            raise SecretStorageError(
                "Could not read the saved credential from the operating-system vault."
            ) from error

    def set(self, integration, secret):
        if not secret:
            raise ValueError("API key cannot be empty.")
        self._backend()
        try:
            keyring.set_password(SERVICE_NAME, integration, secret)
        except Exception as error:
            raise SecretStorageError(
                "Could not save the credential to the operating-system vault."
            ) from error

    def delete(self, integration):
        self._backend()
        try:
            keyring.delete_password(SERVICE_NAME, integration)
        except PasswordDeleteError:
            return
        except KeyringError as error:
            raise SecretStorageError(
                "Could not remove the credential from the operating-system vault."
            ) from error
