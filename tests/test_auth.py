import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from notification_watcher.auth import AuthError, sign_in


class _FakeResponse:
    def __init__(self, payload: dict[str, str]):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_sign_in_reads_error_field(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_req: object, timeout: int = 0) -> object:
        raise HTTPError(
            "https://tradedesky.chapilabs.com/api/desktop/auth",
            401,
            "Unauthorized",
            hdrs=None,
            fp=BytesIO(json.dumps({"error": "Invalid credentials"}).encode()),
        )

    monkeypatch.setattr("notification_watcher.auth.urllib.request.urlopen", fail)
    with pytest.raises(AuthError, match="Invalid credentials"):
        sign_in("user@example.com", "secret")


def test_sign_in_reads_fastapi_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_req: object, timeout: int = 0) -> object:
        raise HTTPError(
            "https://tradedesky.chapilabs.com/api/desktop/auth",
            402,
            "Payment Required",
            hdrs=None,
            fp=BytesIO(json.dumps({"detail": "Active subscription required"}).encode()),
        )

    monkeypatch.setattr("notification_watcher.auth.urllib.request.urlopen", fail)
    with pytest.raises(AuthError, match="Active subscription required"):
        sign_in("user@example.com", "secret")


def test_sign_in_cloudflare_1010(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_req: object, timeout: int = 0) -> object:
        raise HTTPError(
            "https://tradedesky.chapilabs.com/api/desktop/auth",
            403,
            "Forbidden",
            hdrs=None,
            fp=BytesIO(b"error code: 1010\n"),
        )

    monkeypatch.setattr("notification_watcher.auth.urllib.request.urlopen", fail)
    with pytest.raises(AuthError, match="Cloudflare blocked"):
        sign_in("user@example.com", "secret")


def test_sign_in_sends_product_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def ok(req: object, timeout: int = 0) -> _FakeResponse:
        captured["ua"] = req.get_header("User-agent")  # type: ignore[attr-defined]
        return _FakeResponse(
            {
                "api_key": "key-1",
                "ingest_url": "https://trade-receiver.chapilabs.com/v1/ingest",
                "email": "user@example.com",
            }
        )

    monkeypatch.setattr("notification_watcher.auth.urllib.request.urlopen", ok)
    result = sign_in("user@example.com", "secret")
    assert captured["ua"].startswith("TradeDeskyWatcher/")
    assert result["auth_token"] == "key-1"
    assert result["account_email"] == "user@example.com"
