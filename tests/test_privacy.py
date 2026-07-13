from support_trend_detection.preprocessing import normalize_text
from support_trend_detection.privacy import redact_text


def test_redact_text_masks_email_url_and_account_like_id() -> None:
    text = "Contact user@example.com at https://internal.example.test for acct-123456."

    redacted = redact_text(text)

    assert "user@example.com" not in redacted
    assert "https://internal.example.test" not in redacted
    assert "acct-123456" not in redacted
    assert "[redacted-email]" in redacted
    assert "[redacted-url]" in redacted
    assert "[redacted-id]" in redacted


def test_normalize_text_is_deterministic() -> None:
    assert normalize_text("CSV Export TIMEOUT!!!") == "csv export timeout"
