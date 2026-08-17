from pathlib import Path

CI = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"
SIGN = Path(__file__).resolve().parent.parent / "scripts" / "sign_and_notarize_mac.sh"


def test_ci_macos_job_signs_and_notarizes():
    ci = CI.read_text(encoding="utf-8")
    assert "scripts/ci_macos_keychain.sh" in ci
    assert "scripts/sign_and_notarize_mac.sh" in ci
    assert "MACOS_CERTIFICATE_P12_BASE64" in ci
    assert "MACOS_CERTIFICATE_PASSWORD" in ci
    assert "APPLE_API_KEY" in ci
    assert "APPLE_API_KEY_ID" in ci
    assert "APPLE_API_ISSUER" in ci
    assert "REQUIRE_SIGNING: \"1\"" in ci
    assert "MACOS_SIGN_IDENTITY" in ci


def test_ci_windows_job_uses_azure_artifact_signing():
    ci = CI.read_text(encoding="utf-8")
    assert "azure/login@v2" in ci
    assert "azure/artifact-signing-action@v2" in ci
    assert "id-token: write" in ci
    assert "AZURE_CLIENT_ID" in ci
    assert "AZURE_TENANT_ID" in ci
    assert "AZURE_SUBSCRIPTION_ID" in ci
    assert "AZURE_TRUSTED_SIGNING_ENDPOINT" in ci
    assert "AZURE_TRUSTED_SIGNING_ACCOUNT" in ci
    assert "AZURE_CERT_PROFILE_NAME" in ci
    assert "TradeDeskyWatcher.exe" in ci
    assert "timestamp.acs.microsoft.com" in ci


def test_ci_release_purges_cloudflare_desktop_cache():
    ci = CI.read_text(encoding="utf-8")
    assert "scripts/purge_cloudflare_desktop_cache.py" in ci
    assert "CLOUDFLARE_ZONE_ID" in ci
    assert "CLOUDFLARE_API_TOKEN" in ci


def test_sign_script_rejects_non_developer_id():
    text = SIGN.read_text(encoding="utf-8")
    assert "REQUIRE_SIGNING" in text
    assert "Developer ID Application" in text
    assert "notarytool submit" in text
    assert "APPLE_API_KEY_FILE" in text
