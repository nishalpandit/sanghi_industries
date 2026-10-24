"""
OTP service module: generation, hashing, verification, and console-based sending.
Replace the `send_otp` function with a real SMS gateway (Twilio, MSG91, etc.) in production.
"""
import random
import hashlib
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import OTPRecord


def generate_otp():
    """Generate a random numeric OTP of configured length."""
    length = getattr(settings, 'OTP_LENGTH', 6)
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


def hash_otp(otp: str) -> str:
    """Hash an OTP using SHA-256 for secure storage."""
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp_hash(plain_otp: str, otp_hash: str) -> bool:
    """Verify a plain OTP against its stored hash."""
    return hash_otp(plain_otp) == otp_hash


def send_otp(mobile_number: str, otp: str, purpose: str):
    """
    Send OTP to the given mobile number.
    Currently logs to console. Replace with SMS gateway in production.
    """
    print(f'\n{"="*50}')
    print(f'  OTP for {mobile_number} ({purpose}): {otp}')
    print(f'{"="*50}\n')


def create_otp_record(mobile_number: str, purpose: str) -> str:
    """
    Generate OTP, hash it, store the record, and send it.
    Returns the plain OTP (for development/testing purposes).
    """
    otp = generate_otp()
    expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 5)
    expires_at = timezone.now() + timedelta(minutes=expiry_minutes)

    OTPRecord.objects.create(
        mobile_number=mobile_number,
        otp_hash=hash_otp(otp),
        purpose=purpose,
        expires_at=expires_at,
    )

    send_otp(mobile_number, otp, purpose)
    return otp


def can_resend_otp(mobile_number: str) -> bool:
    """Check if enough time has passed since the last OTP was sent."""
    cooldown = getattr(settings, 'OTP_RESEND_COOLDOWN_SECONDS', 60)
    cutoff = timezone.now() - timedelta(seconds=cooldown)
    recent = OTPRecord.objects.filter(
        mobile_number=mobile_number,
        created_at__gte=cutoff,
    ).exists()
    return not recent
