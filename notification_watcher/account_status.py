from notification_watcher.types import AppConfig


def format_status_line(base: str, config: AppConfig) -> str:
    if config.is_signed_in():
        email = config.account_email or "signed in"
        if base == "Watching":
            return f"Watching · signed in as {email}"
        return f"{base} · signed in as {email}"
    if base == "Watching":
        return "Watching (not signed in)"
    return base
