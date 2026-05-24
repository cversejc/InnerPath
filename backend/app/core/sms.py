import random
from typing import Optional
from app.core.cache import cache_set, cache_get, cache_delete
from app.config import settings


async def send_verification_code(phone: str) -> bool:
    """
    Send SMS verification code

    In production, integrate with Aliyun SMS or Tencent Cloud SMS
    For development, we'll just store the code in Redis
    """
    # Generate 6-digit code
    code = str(random.randint(100000, 999999))

    # Store in Redis with 5-minute expiration
    cache_key = f"sms:code:{phone}"
    await cache_set(cache_key, code, expire=300)

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


async def verify_code(phone: str, code: str) -> bool:
    """Verify SMS code"""
    cache_key = f"sms:code:{phone}"
    stored_code = await cache_get(cache_key)

    if stored_code and stored_code == code:
        # Delete code after successful verification
        await cache_delete(cache_key)
        return True

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
