import json
import urllib.error
import urllib.request

from notification_watcher.product import DEFAULT_INGEST_URL, DEFAULT_PLATFORM_URL, HTTP_USER_AGENT


class AuthError(Exception):
    pass


def _message_from_http_error(exc: urllib.error.HTTPError) -> str:
    raw = ""
    try:
        raw = exc.read().decode("utf-8", errors="replace")
        body = json.loads(raw)
        message = body.get("error") or body.get("detail")
        if isinstance(message, str) and message:
            return message
    except (json.JSONDecodeError, OSError, AttributeError):
        pass
    if "1010" in raw:
        return "Cloudflare blocked this app. Update Trade Desky Watcher and try again."
    if exc.code:
        return f"Sign in failed (HTTP {exc.code})"
    return "Sign in failed"


def sign_in(email: str, password: str, platform_url: str | None = None) -> dict[str, str]:
    base = (platform_url or DEFAULT_PLATFORM_URL).rstrip("/")
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/desktop/auth",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": HTTP_USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise AuthError(_message_from_http_error(exc)) from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise AuthError(f"Could not reach platform: {exc}") from exc

    api_key = data.get("api_key")
    ingest_url = data.get("ingest_url") or DEFAULT_INGEST_URL
    account_email = data.get("email") or email
    if not api_key:
        raise AuthError("Platform did not return a device token")
    return {
        "auth_token": api_key,
        "ingest_url": ingest_url,
        "account_email": account_email,
    }
