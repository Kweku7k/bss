import logging
import random
from datetime import timedelta
from typing import Tuple

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import OneTimePassword, User

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_TTL_MINUTES = 5


def _generate_numeric_code(length: int = OTP_LENGTH) -> str:
    return ''.join(random.choices('0123456789', k=length))


def create_otp(user: User, length: int = OTP_LENGTH, ttl_minutes: int = OTP_TTL_MINUTES) -> OneTimePassword:
    """
    Create a fresh OTP for the given user, invalidating any active codes.
    """
    now = timezone.now()

    (
        OneTimePassword.objects
        .filter(user=user, is_used=False, expires_at__gt=now)
        .update(is_used=True)
    )

    code = _generate_numeric_code(length)
    expires_at = now + timedelta(minutes=ttl_minutes)

    otp = OneTimePassword.objects.create(
        user=user,
        code=code,
        expires_at=expires_at,
    )

    logger.info("Generated OTP for user %s with expiry at %s", user.pk, expires_at.isoformat())
    return otp


def send_otp_email(user: User, otp: OneTimePassword) -> None:
    """
    Dispatch the OTP to the user's registered email address.
    """
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None)
    subject = "Your One-Time Verification Code"

    greeting = user.first_name or user.username or user.email
    message = (
        f"Hello {greeting},\n\n"
        f"Your one-time verification code is {otp.code}. "
        f"The code expires at {otp.expires_at.strftime('%Y-%m-%d %H:%M:%S %Z')}.\n\n"
        "If you did not try to sign in, please ignore this email.\n\n"
        "Best regards,\n"
        "Central University ERP Team"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info("Sent OTP email to user %s at %s", user.pk, user.email)


def generate_and_send_otp(user: User) -> OneTimePassword:
    otp = create_otp(user)
    send_otp_email(user, otp)
    return otp


def send_welcome_email(user: User) -> None:
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None)
    if not user.email:
        logger.warning("Skipping welcome email for user %s: no email address", user.pk)
        return

    greeting = user.first_name or user.username or "there"
    subject = "Welcome to Central University ERP"
    message = (
        f"Hello {greeting},\n\n"
        "Thank you for signing up for the Central University ERP portal.\n\n"
        "Our administrator and HR team will review your account shortly. "
        "Once your details are verified, your roles and permissions will be assigned "
        "and you will receive a confirmation email letting you know that you can log in fully.\n\n"
        "If you did not create this account or have any questions, please contact the HR support desk.\n\n"
        "Warm regards,\n"
        "Central University ERP Team"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info("Sent welcome email to new user %s at %s", user.pk, user.email)


def verify_otp(user: User, submitted_code: str) -> Tuple[bool, str]:
    """
    Validate an OTP for the given user.
    Returns (is_valid, message).
    """
    now = timezone.now()

    try:
        otp = (
            OneTimePassword.objects
            .filter(user=user, code=submitted_code)
            .latest('created_at')
        )
    except OneTimePassword.DoesNotExist:
        return False, "Invalid verification code."

    if otp.is_used:
        return False, "This verification code has already been used."

    if otp.expires_at <= now:
        otp.is_used = True
        otp.save(update_fields=['is_used'])
        return False, "This verification code has expired."

    otp.is_used = True
    otp.save(update_fields=['is_used'])
    return True, "Verification successful."

