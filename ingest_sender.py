"""
Send notifications to the Trade Platform ingest endpoint. Non-blocking; uses daemon threads.
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request

from notification_watcher import format_delivered_date, to_unix_timestamp
from notification_watcher.config import get_app_logger, load_config
from notification_watcher.product import HTTP_USER_AGENT
from notification_watcher.types import AppConfig

REQUEST_TIMEOUT = 10
RETRY_DELAYS = (1.0, 3.0, 9.0)

_last_ingest_status: str = "Not connected"
_last_ingest_time: float | None = None


def get_last_ingest_status() -> tuple[str, float | None]:
    return _last_ingest_status, _last_ingest_time


def _set_last_ingest_status(status: str) -> None:
    global _last_ingest_status, _last_ingest_time
    _last_ingest_status = status
    _last_ingest_time = time.time()


def _platform_name() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    return "unknown"


def build_generic_payload(
    app_id: str,
    title: str,
    subtitle: str,
    body: str,
    delivered_date: float | None,
) -> dict:
    unix_ts = to_unix_timestamp(delivered_date)
    return {
        "app_id": app_id,
        "title": title,
        "subtitle": subtitle,
        "body": body,
        "delivered_date": unix_ts,
        "delivered_date_iso": format_delivered_date(delivered_date),
        "platform": _platform_name(),
    }


def build_payload(
    app_id: str,
    title: str,
    subtitle: str,
    body: str,
    delivered_date: float | None,
) -> tuple[bytes, str]:
    payload = build_generic_payload(app_id, title, subtitle, body, delivered_date)
    payload_json = json.dumps(payload, ensure_ascii=False)
    return payload_json.encode("utf-8"), payload_json


def _post_one(url: str, payload_bytes: bytes, payload_json: str, auth_token: str) -> bool:
    logger = get_app_logger()
    logger.info("Payload: %s", payload_json)
    for h in logger.handlers:
        h.flush()
    req = urllib.request.Request(
        url,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
            "User-Agent": HTTP_USER_AGENT,
        },
        method="POST",
    )
    for attempt, delay in enumerate((0.0, *RETRY_DELAYS)):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                status = getattr(resp, "status", None)
                body = resp.read().decode("utf-8", errors="replace")
                body_preview = body[:500] + "..." if len(body) > 500 else body
                logger.info(
                    "Ingest sent to %s | status=%s | response: %s",
                    url[:50],
                    status,
                    body_preview or "(empty)",
                )
                _set_last_ingest_status(f"OK ({status})")
                return True
        except urllib.error.HTTPError as e:
            try:
                response_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                response_body = ""
            body_preview = (
                response_body[:500] + "..."
                if len(response_body) > 500
                else response_body or "(empty)"
            )
            logger.warning(
                "Ingest failed %s | status=%s | response: %s (attempt %d)",
                url[:50],
                e.code,
                body_preview,
                attempt + 1,
            )
            if attempt >= len(RETRY_DELAYS):
                _set_last_ingest_status(f"Failed HTTP {e.code}")
                return False
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            logger.warning("Ingest failed %s: %s (attempt %d)", url[:50], e, attempt + 1)
            if attempt >= len(RETRY_DELAYS):
                _set_last_ingest_status(f"Failed: {e}")
                return False
    return False


def _should_forward(app_id: str) -> bool:
    return "discord" in app_id.lower()


def send_notification(
    app_id: str,
    title: str,
    subtitle: str,
    body: str,
    delivered_date: float | None,
    config: AppConfig | None = None,
) -> None:
    cfg = config or load_config()
    if not _should_forward(app_id):
        return
    if not cfg.auth_token:
        get_app_logger().info("Notification skipped: not signed in")
        return
    get_app_logger().info(
        "Notification: %s | %s",
        title or "(no title)",
        body[:80] + "..." if len(body) > 80 else body,
    )

    def run_send() -> None:
        payload_bytes, payload_json = build_payload(
            app_id, title, subtitle, body, delivered_date
        )
        _post_one(cfg.ingest_url.strip(), payload_bytes, payload_json, cfg.auth_token)

    threading.Thread(target=run_send, daemon=True).start()


def send_test_connection() -> tuple[bool, str]:
    config = load_config()
    if not config.auth_token:
        return False, "Sign in to test the connection"
    payload_bytes, payload_json = build_payload(
        "com.notificationwatcher.test",
        "Test notification",
        "Connection test",
        "If you see this, ingest is working.",
        None,
    )
    ok = _post_one(
        config.ingest_url.strip(),
        payload_bytes,
        payload_json,
        config.auth_token,
    )
    return ok, "Connection test sent" if ok else get_last_ingest_status()[0]
