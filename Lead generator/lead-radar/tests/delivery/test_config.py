import pytest

from delivery.config import DeliveryConfig, load_config


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("DELIVERY_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("DELIVERY_SMTP_PORT", "587")
    monkeypatch.setenv("DELIVERY_SMTP_USER", "marieke@lead-radar.nl")
    monkeypatch.setenv("DELIVERY_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("DELIVERY_SMTP_USE_TLS", "true")
    monkeypatch.setenv("DELIVERY_REPLY_DOMAIN", "lead-radar.nl")
    monkeypatch.setenv("DELIVERY_DRY_RUN", "false")
    cfg = load_config()
    assert isinstance(cfg, DeliveryConfig)
    assert cfg.smtp_host == "smtp.example.com"
    assert cfg.smtp_port == 587
    assert cfg.smtp_user == "marieke@lead-radar.nl"
    assert cfg.smtp_use_tls is True
    assert cfg.reply_domain == "lead-radar.nl"
    assert cfg.dry_run is False


def test_dry_run_default_true_when_unset(monkeypatch):
    for var in ("DELIVERY_DRY_RUN",):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("DELIVERY_REPLY_DOMAIN", "lead-radar.nl")
    cfg = load_config()
    assert cfg.dry_run is True


def test_missing_reply_domain_raises(monkeypatch):
    monkeypatch.delenv("DELIVERY_REPLY_DOMAIN", raising=False)
    with pytest.raises(ValueError, match="DELIVERY_REPLY_DOMAIN"):
        load_config()


def test_smtp_required_when_not_dry_run(monkeypatch):
    monkeypatch.setenv("DELIVERY_REPLY_DOMAIN", "lead-radar.nl")
    monkeypatch.setenv("DELIVERY_DRY_RUN", "false")
    monkeypatch.delenv("DELIVERY_SMTP_HOST", raising=False)
    monkeypatch.delenv("DELIVERY_SMTP_USER", raising=False)
    monkeypatch.delenv("DELIVERY_SMTP_PASSWORD", raising=False)
    with pytest.raises(ValueError, match="SMTP"):
        load_config()
