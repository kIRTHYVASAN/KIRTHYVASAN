import pytest

import settings_store


class _FakeKeyringErrors:
    class PasswordDeleteError(Exception):
        pass


class _FakeKeyring:
    """In-memory stand-in for the OS credential store, so tests don't touch
    a real Windows Credential Manager / Keychain / Secret Service backend."""

    def __init__(self):
        self.store: dict[tuple[str, str], str] = {}
        self.errors = _FakeKeyringErrors()

    def get_keyring(self):
        return self

    def set_password(self, service, field, value):
        self.store[(service, field)] = value

    def get_password(self, service, field):
        return self.store.get((service, field))

    def delete_password(self, service, field):
        if (service, field) not in self.store:
            raise self.errors.PasswordDeleteError()
        del self.store[(service, field)]


@pytest.fixture
def fake_keyring(monkeypatch):
    fake = _FakeKeyring()
    monkeypatch.setattr(settings_store, "keyring", fake)
    return fake


def test_save_and_load_round_trip(fake_keyring):
    settings_store.save_credentials(GROWW_API_KEY="key123", GROWW_TOTP_SECRET="totp123")
    creds = settings_store.load_credentials()
    assert creds["GROWW_API_KEY"] == "key123"
    assert creds["GROWW_TOTP_SECRET"] == "totp123"
    assert creds["GROWW_API_SECRET"] is None


def test_has_credentials_true_with_key_and_totp(fake_keyring):
    settings_store.save_credentials(GROWW_API_KEY="key123", GROWW_TOTP_SECRET="totp123")
    assert settings_store.has_credentials() is True


def test_has_credentials_false_without_any_secret(fake_keyring):
    settings_store.save_credentials(GROWW_API_KEY="key123")
    assert settings_store.has_credentials() is False


def test_clear_credentials_removes_everything(fake_keyring):
    settings_store.save_credentials(GROWW_API_KEY="key123", GROWW_API_SECRET="sec456")
    settings_store.clear_credentials()
    creds = settings_store.load_credentials()
    assert all(value is None for value in creds.values())


def test_saving_falsy_value_deletes_existing_field(fake_keyring):
    settings_store.save_credentials(GROWW_API_KEY="key123", GROWW_TOTP_SECRET="totp123")
    settings_store.save_credentials(GROWW_API_KEY="key123", GROWW_TOTP_SECRET=None)
    creds = settings_store.load_credentials()
    assert creds["GROWW_API_KEY"] == "key123"
    assert creds["GROWW_TOTP_SECRET"] is None


def test_save_credentials_returns_true_when_backend_works(fake_keyring):
    assert settings_store.save_credentials(GROWW_API_KEY="key123") is True


def test_broken_backend_degrades_instead_of_raising(monkeypatch):
    class BrokenKeyring:
        def get_keyring(self):
            raise RuntimeError("no backend available")

        def get_password(self, *a):
            raise RuntimeError("no backend available")

        def set_password(self, *a):
            raise RuntimeError("no backend available")

        def delete_password(self, *a):
            raise RuntimeError("no backend available")

    monkeypatch.setattr(settings_store, "keyring", BrokenKeyring())

    assert settings_store.is_available() is False
    assert settings_store.save_credentials(GROWW_API_KEY="key123") is False
    assert settings_store.load_credentials() == {f: None for f in settings_store.FIELDS}
    assert settings_store.has_credentials() is False


def test_backend_panic_via_baseexception_also_degrades(monkeypatch):
    """Regression test: a native backend (e.g. a broken `cryptography`
    install) can panic with an exception that inherits directly from
    BaseException, not Exception -- a bare `except Exception` would miss it
    and crash the whole Settings tab."""

    class NativePanic(BaseException):
        pass

    class PanickingKeyring:
        def get_keyring(self):
            raise NativePanic("native backend panicked")

        def get_password(self, *a):
            raise NativePanic("native backend panicked")

        def set_password(self, *a):
            raise NativePanic("native backend panicked")

        def delete_password(self, *a):
            raise NativePanic("native backend panicked")

    monkeypatch.setattr(settings_store, "keyring", PanickingKeyring())

    assert settings_store.is_available() is False
    assert settings_store.save_credentials(GROWW_API_KEY="key123") is False
    assert settings_store.load_credentials()["GROWW_API_KEY"] is None
