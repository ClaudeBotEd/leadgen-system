from email.message import EmailMessage

from delivery.config import DeliveryConfig
from delivery.send import build_email_message, send_smtp


def make_config(dry_run=False):
    return DeliveryConfig(
        reply_domain="lead-radar.nl",
        dry_run=dry_run,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="marieke@lead-radar.nl",
        smtp_password="secret",
        smtp_use_tls=True,
    )


def test_build_message_sets_required_headers():
    msg = build_email_message(
        subject="Amsterdam · warmtepomp · HOT",
        preheader="Marieke reviewde een Tweakers-post uit regio Amsterdam.",
        from_display="Marieke de Vries — Lead Radar",
        from_address="marieke@lead-radar.nl",
        to_display="Jeroen Visser",
        to_address="jeroen@visserinstallaties.nl",
        body_text="hello",
        body_html="<p>hello</p>",
        case_id="LR-2026-05-18-0042",
    )
    assert msg["From"].startswith("Marieke de Vries")
    assert msg["From"].endswith("<marieke@lead-radar.nl>")
    assert msg["To"] == "Jeroen Visser <jeroen@visserinstallaties.nl>"
    assert msg["Reply-To"] == "marieke@lead-radar.nl"
    assert msg["Subject"] == "Amsterdam · warmtepomp · HOT"
    assert msg["X-LeadRadar-Case-ID"] == "LR-2026-05-18-0042"


def test_build_message_has_text_and_html_alternatives():
    msg = build_email_message(
        subject="s",
        preheader="p",
        from_display="F",
        from_address="f@x.nl",
        to_display="T",
        to_address="t@x.nl",
        body_text="plain",
        body_html="<p>h</p>",
        case_id="LR-2026-05-18-0001",
    )
    payloads = msg.get_payload()
    assert isinstance(payloads, list) and len(payloads) == 2
    types = {p.get_content_type() for p in payloads}
    assert types == {"text/plain", "text/html"}


def test_send_smtp_calls_smtplib(monkeypatch):
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port):
            captured["host"] = host
            captured["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            captured["starttls"] = True

        def login(self, user, pw):
            captured["login"] = (user, pw)

        def send_message(self, msg):
            captured["subject"] = msg["Subject"]

    import delivery.send as send_mod

    monkeypatch.setattr(send_mod.smtplib, "SMTP", FakeSMTP)

    msg = EmailMessage()
    msg["From"] = "Marieke <marieke@lead-radar.nl>"
    msg["To"] = "Jeroen <jeroen@x.nl>"
    msg["Subject"] = "test"
    send_smtp(msg, make_config(dry_run=False))

    assert captured["host"] == "smtp.example.com"
    assert captured["port"] == 587
    assert captured["starttls"] is True
    assert captured["login"] == ("marieke@lead-radar.nl", "secret")
    assert captured["subject"] == "test"


def test_send_smtp_skips_when_dry_run(monkeypatch):
    called = {"smtp": False}

    class FakeSMTP:
        def __init__(self, *a, **kw):
            called["smtp"] = True

    import delivery.send as send_mod

    monkeypatch.setattr(send_mod.smtplib, "SMTP", FakeSMTP)

    msg = EmailMessage()
    msg["From"] = "a@x"
    msg["To"] = "b@x"
    msg["Subject"] = "t"
    assert send_smtp(msg, make_config(dry_run=True)) == "dry-run"
    assert called["smtp"] is False
