"""Tests voor utils.email_extractor.extract_emails (legacy module).

Regressie-bug: html.unescape() werd gebruikt zonder `import html` →
elke call raised NameError. Legacy code (root utils/), geen onderdeel
van de consumer-pipeline.
"""
from __future__ import annotations


def test_extract_emails_does_not_crash_on_html_entities() -> None:
    """Regression: was NameError op html.unescape() zonder import."""
    from utils.email_extractor import extract_emails
    result = extract_emails("contact us at info&#64;example.com")
    assert isinstance(result, list)


def test_extract_emails_plain_text() -> None:
    """Echte domeinen worden gevonden; example.com staat op blacklist."""
    from utils.email_extractor import extract_emails
    result = extract_emails("Email me at jan@vakman-utrecht.nl voor offerte")
    assert "jan@vakman-utrecht.nl" in result


def test_extract_emails_returns_empty_on_empty_input() -> None:
    from utils.email_extractor import extract_emails
    assert extract_emails("") == []
