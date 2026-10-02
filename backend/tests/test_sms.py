import pytest

from app.core import sms


@pytest.mark.asyncio
async def test_missing_sms_provider_fails_even_in_development(monkeypatch):
    monkeypatch.setattr(sms.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(sms.settings, "SMS_SPUG_TOKEN", "")
    monkeypatch.setattr(sms.settings, "SMS_DEV_CODE_LOGGING", False)

    with pytest.raises(sms.SmsProviderNotConfigured):
        await sms._deliver_sms("13800000000", "123456")


@pytest.mark.asyncio
async def test_development_code_logging_requires_explicit_opt_in(monkeypatch, capsys):
    monkeypatch.setattr(sms.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(sms.settings, "SMS_SPUG_TOKEN", "")
    monkeypatch.setattr(sms.settings, "SMS_DEV_CODE_LOGGING", True)

    await sms._deliver_sms("13800000000", "123456")

    assert "[DEV] SMS Code for 138****0000: 123456" in capsys.readouterr().out
