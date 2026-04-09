"""
Django signals for automatic cache invalidation
Ensures blocked IPs/users cache stays fresh when models change
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='main.BlockedIP')
@receiver(post_delete, sender='main.BlockedIP')
def invalidate_blocked_ips_cache(sender, instance, **kwargs):
    """Invalidate blocked IPs cache when BlockedIP model changes"""
    try:
        from main.middleware.realtime_ip_blocker import realtime_blocker
        realtime_blocker._invalidate_cache()
        logger.debug(f"Cache invalidated due to BlockedIP change: {instance.ip_address}")
    except Exception as e:
        logger.warning(f"Error invalidating cache for BlockedIP: {e}")


@receiver(post_save, sender='main.BlockedUser')
@receiver(post_delete, sender='main.BlockedUser')
def invalidate_blocked_users_cache(sender, instance, **kwargs):
    """Invalidate blocked users cache when BlockedUser model changes"""
    try:
        from main.middleware.realtime_ip_blocker import realtime_blocker
        realtime_blocker._invalidate_cache()
        logger.debug(f"Cache invalidated due to BlockedUser change: {instance.user.username if hasattr(instance, 'user') else 'unknown'}")
    except Exception as e:
        logger.warning(f"Error invalidating cache for BlockedUser: {e}")

