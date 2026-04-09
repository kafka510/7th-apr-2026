from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from accounts.models import (
    Capability,
    Feature,
    Role,
    RoleCapability,
    RoleFeature,
)


def _invalidate_permissions_cache():
    from main.permissions import invalidate_permissions_cache

    invalidate_permissions_cache()


@receiver(post_save, sender=Feature)
@receiver(post_delete, sender=Feature)
@receiver(post_save, sender=Capability)
@receiver(post_delete, sender=Capability)
@receiver(post_save, sender=Role)
@receiver(post_delete, sender=Role)
@receiver(post_save, sender=RoleFeature)
@receiver(post_delete, sender=RoleFeature)
@receiver(post_save, sender=RoleCapability)
@receiver(post_delete, sender=RoleCapability)
def _permissions_changed(sender, **kwargs):
    """
    Whenever role/feature definitions change, clear the cached permission snapshot so
    newly added features become available without restarting the application.
    """

    _invalidate_permissions_cache()

