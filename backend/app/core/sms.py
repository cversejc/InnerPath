import hashlib
import hmac
import secrets
from urllib.parse import quote

import httpx

from app.config import settings
from app.core.cache import (
    cache_compare_and_delete,
    cache_delete,
    cache_get,
    cache_increment,
    cache_set,
    cache_set_if_absent,
)

CODE_TTL_SECONDS = 600
RESEND_COOLDOWN_SECONDS = 60
MAX_CODE_ATTEMPTS = 5


class SmsError(Exception):
    pass


class SmsCooldownError(SmsError):
    pass


class SmsRateLimitError(SmsError):
    pass


class SmsProviderNotConfigured(SmsError):
    pass


class SmsDeliveryError(SmsError):
    pass


def _code_digest(phone: str, code: str, purpose: str) -> str:
    payload = f"{purpose}:{phone}:{code}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


async def enforce_sms_rate_limit(phone: str, ip_address: str | None = None) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return

    limit = max(settings.RATE_LIMIT_SMS_PER_MINUTE, 1)
    keys = [f"sms:rate:phone:{phone}"]
    if ip_address:
        keys.append(f"sms:rate:ip:{ip_address}")

    for key in keys:
        if await cache_increment(key, expire=60) > limit:
            raise SmsRateLimitError


async def _deliver_sms(phone: str, code: str) -> None:
    if not settings.SMS_SPUG_TOKEN:
        if settings.ENVIRONMENT == "development" and settings.SMS_DEV_CODE_LOGGING:
            print(f"[DEV] SMS Code for {phone[:3]}****{phone[-4:]}: {code}")
            return
        raise SmsProviderNotConfigured

    url = f"https://push.spug.cc/sms/{quote(settings.SMS_SPUG_TOKEN, safe='')}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params={"to": phone, "code": code})
            response.raise_for_status()
            result = response.json()
            if isinstance(result, dict):
                provider_code = result.get("code")
                normalized_code = str(provider_code).strip().lower() if provider_code is not None else None
                if normalized_code == "403":
                    raise SmsDeliveryError("SMS provider account verification required")
                if normalized_code is not None and normalized_code not in {"0", "200"}:
                    raise SmsDeliveryError("SMS provider rejected the request")
                if result.get("success") is False:
                    raise SmsDeliveryError("SMS provider rejected the request")
    except (httpx.HTTPError, ValueError):
        raise SmsDeliveryError from None


async def send_verification_code(phone: str, purpose: str = "register") -> None:
    code = str(secrets.randbelow(900000) + 100000)
    cache_key = f"sms:code:{purpose}:{phone}"
    cooldown_key = f"sms:cooldown:{phone}"
    cooldown_token = secrets.token_urlsafe(16)

    if not await cache_set_if_absent(cooldown_key, cooldown_token, expire=RESEND_COOLDOWN_SECONDS):
        raise SmsCooldownError

    await cache_set(cache_key, _code_digest(phone, code, purpose), expire=CODE_TTL_SECONDS)
    await cache_delete(f"sms:attempts:{purpose}:{phone}")
    try:
        await _deliver_sms(phone, code)
    except (SmsDeliveryError, SmsProviderNotConfigured):
        await cache_delete(cache_key)
        await cache_compare_and_delete(cooldown_key, cooldown_token)
        raise


async def verify_code(phone: str, code: str, purpose: str = "register") -> bool:
    cache_key = f"sms:code:{purpose}:{phone}"
    attempts_key = f"sms:attempts:{purpose}:{phone}"
    attempts = await cache_increment(attempts_key, expire=CODE_TTL_SECONDS)
    if attempts > MAX_CODE_ATTEMPTS:
        await cache_delete(cache_key)
        return False

    stored_digest = await cache_get(cache_key)
    candidate_digest = _code_digest(phone, code, purpose)
    if stored_digest and hmac.compare_digest(stored_digest, candidate_digest):
        if not await cache_compare_and_delete(cache_key, stored_digest):
            return False
        await cache_delete(attempts_key)
        return True

    return False
