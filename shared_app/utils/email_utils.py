"""
Email subject helpers: prepend env/prefix from settings so emails can be
differentiated by purpose and environment (dev vs prod). Load EMAIL_SUBJECT_PREFIX from .env.
"""

from django.conf import settings


def build_email_subject(subject: str) -> str:
    """
    Prepend EMAIL_SUBJECT_PREFIX to the subject when set (e.g. "[DEV]", "[PROD]").

    Use for all system emails (data collection, security alerts) so recipients can
    filter and identify environment and purpose. Load EMAIL_SUBJECT_PREFIX from .env.
    """
    prefix = getattr(settings, "EMAIL_SUBJECT_PREFIX", "").strip()
    if not prefix:
        return subject
    return f"{prefix} {subject}"
