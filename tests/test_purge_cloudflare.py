import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from notification_watcher.product import desktop_cache_purge_urls
from scripts.purge_cloudflare_desktop_cache import purge_urls


class _FakeResponse:
    def __init__(self, payload: dict[str, object]):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_desktop_cache_purge_urls():
    urls = desktop_cache_purge_urls("https://tradedesky.chapilabs.com")
    assert urls == [
        "https://tradedesky.chapilabs.com/desktop/TradeDeskyWatcher.dmg",
        "https://tradedesky.chapilabs.com/desktop/TradeDeskyWatcher-setup.exe",
        "https://tradedesky.chapilabs.com/desktop/TradeDeskyWatcher-win.zip",
        "https://tradedesky.chapilabs.com/desktop/appcast.xml",
    ]


def test_purge_urls_posts_files(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def ok(req: object, timeout: int = 0) -> _FakeResponse:
        captured["url"] = req.full_url  # type: ignore[attr-defined]
        captured["body"] = json.loads(req.data.decode("utf-8"))  # type: ignore[attr-defined]
        captured["auth"] = req.get_header("Authorization")  # type: ignore[attr-defined]
        return _FakeResponse({"success": True, "result": {"id": "ok"}})

    monkeypatch.setattr("scripts.purge_cloudflare_desktop_cache.urlopen", ok)
    payload = purge_urls("zone-1", "token-1", ["https://example.com/desktop/TradeDeskyWatcher.dmg"])
    assert payload["success"] is True
    assert captured["url"].endswith("/zones/zone-1/purge_cache")
    assert captured["body"] == {"files": ["https://example.com/desktop/TradeDeskyWatcher.dmg"]}
    assert captured["auth"] == "Bearer token-1"


def test_purge_urls_rejects_unsuccessful_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    def ok(_req: object, timeout: int = 0) -> _FakeResponse:
        return _FakeResponse({"success": False, "errors": [{"message": "denied"}]})

    monkeypatch.setattr("scripts.purge_cloudflare_desktop_cache.urlopen", ok)
    with pytest.raises(SystemExit, match="Cloudflare purge failed"):
        purge_urls("zone-1", "token-1", ["https://example.com/a"])


def test_purge_urls_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_req: object, timeout: int = 0) -> object:
        raise HTTPError(
            "https://api.cloudflare.com/client/v4/zones/zone-1/purge_cache",
            403,
            "Forbidden",
            hdrs=None,
            fp=BytesIO(b'{"success":false}'),
        )

    monkeypatch.setattr("scripts.purge_cloudflare_desktop_cache.urlopen", fail)
    with pytest.raises(HTTPError):
        purge_urls("zone-1", "token-1", ["https://example.com/a"])
