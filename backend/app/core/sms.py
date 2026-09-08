import secrets
from app.core.cache import cache_delete, cache_get, cache_increment, cache_set
from app.config import settings


async def send_verification_code(phone: str, purpose: str = "register") -> bool:
    """
    Send SMS verification code

    In production, integrate with Aliyun SMS or Tencent Cloud SMS
    For development, we'll just store the code in Redis
    """
    # Generate 6-digit code
    code = str(secrets.randbelow(900000) + 100000)

    # Store in Redis with 5-minute expiration
    cache_key = f"sms:code:{purpose}:{phone}"
    cooldown_key = f"sms:cooldown:{purpose}:{phone}"
    if await cache_get(cooldown_key):
        return False

    await cache_set(cache_key, code, expire=300)
    await cache_set(cooldown_key, "1", expire=60)

    # In production, call SMS API here
    if settings.ENVIRONMENT == "development":
        print(f"[DEV] SMS Code for {phone}: {code}")
    else:
        # TODO: Integrate with SMS provider
        # if settings.SMS_PROVIDER == "aliyun":
        #     await send_aliyun_sms(phone, code)
        # elif settings.SMS_PROVIDER == "tencent":
        #     await send_tencent_sms(phone, code)
        pass

    return True


async def verify_code(phone: str, code: str, purpose: str = "register") -> bool:
    """Verify SMS code"""
    cache_key = f"sms:code:{purpose}:{phone}"
    attempts_key = f"sms:attempts:{purpose}:{phone}"
    stored_code = await cache_get(cache_key)

    if await cache_get(attempts_key) and int(await cache_get(attempts_key)) >= 5:
        await cache_delete(cache_key)
        return False

    if stored_code and stored_code == code:
        # Delete code after successful verification
        await cache_delete(cache_key)
        await cache_delete(attempts_key)
        return True

    await cache_increment(attempts_key, expire=300)
    return False


async def send_aliyun_sms(phone: str, code: str):
    """
    Send SMS via Aliyun

    Requires: pip install aliyun-python-sdk-core aliyun-python-sdk-dysmsapi
    """
    # TODO: Implement Aliyun SMS integration
    pass


async def send_tencent_sms(phone: str, code: str):
    """
    Send SMS via Tencent Cloud

    Requires: pip install tencentcloud-sdk-python
    """
    # TODO: Implement Tencent Cloud SMS integration
    pass
