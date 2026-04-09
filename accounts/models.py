from datetime import timedelta

from django.db import models
from django.utils import timezone


class LoginAttempt(models.Model):
    """Track failed login attempts for rate limiting."""

    username = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField()
    attempt_time = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField(default=False)

    class Meta:
        ordering = ["-attempt_time"]
        indexes = [
            models.Index(fields=["username", "-attempt_time"]),
            models.Index(fields=["ip_address", "-attempt_time"]),
        ]

    def __str__(self) -> str:
        return f"{self.username} - {self.ip_address} - {self.attempt_time}"

    @classmethod
    def get_recent_failed_attempts(cls, username, minutes: int = 1) -> int:
        """Get failed login attempts within the last N minutes."""
        time_threshold = timezone.now() - timedelta(minutes=minutes)
        return (
            cls.objects.filter(
                username=username,
                successful=False,
                attempt_time__gte=time_threshold,
            ).count()
        )

    @classmethod
    def get_lockout_time_remaining(cls, username, minutes: int = 1) -> int:
        """Get the time remaining until user can try again."""
        time_threshold = timezone.now() - timedelta(minutes=minutes)
        first_failed_attempt = (
            cls.objects.filter(
                username=username,
                successful=False,
                attempt_time__gte=time_threshold,
            )
            .order_by("attempt_time")
            .first()
        )

        if first_failed_attempt:
            unlock_time = first_failed_attempt.attempt_time + timedelta(minutes=minutes)
            time_remaining = (unlock_time - timezone.now()).total_seconds()
            return max(0, int(time_remaining))
        return 0

    @classmethod
    def is_locked_out(
        cls,
        username,
        max_attempts: int = 3,
        lockout_minutes: int = 1,
    ) -> bool:
        """Check if user is currently locked out."""
        failed_attempts = cls.get_recent_failed_attempts(username, lockout_minutes)
        return failed_attempts >= max_attempts

    @classmethod
    def clear_attempts(cls, username) -> None:
        """Clear all failed attempts for a user (call after successful login)."""
        cls.objects.filter(username=username, successful=False).delete()

    @classmethod
    def cleanup_old_attempts(cls, days: int = 7) -> None:
        """Clean up old login attempts (can be run as a periodic task)."""
        time_threshold = timezone.now() - timedelta(days=days)
        cls.objects.filter(attempt_time__lt=time_threshold).delete()


class Feature(models.Model):
    """Feature toggles or dashboard pages that roles can access."""

    key = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ordering", "name"]

    def __str__(self) -> str:
        return self.name


class Capability(models.Model):
    """Discrete capabilities or powers that roles can grant."""

    key = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self) -> str:
        return self.name


class Role(models.Model):
    """Application role that bundles features and capabilities."""

    key = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    features = models.ManyToManyField(
        Feature,
        related_name="roles",
        through="RoleFeature",
        blank=True,
    )
    capabilities = models.ManyToManyField(
        Capability,
        related_name="roles",
        through="RoleCapability",
        blank=True,
    )

    class Meta:
        ordering = ["ordering", "name"]

    def __str__(self) -> str:
        return self.name


class RoleFeature(models.Model):
    """Link table between roles and features."""

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_features")
    feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        related_name="feature_roles",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("role", "feature")
        ordering = ["role__ordering", "feature__ordering"]

    def __str__(self) -> str:
        return f"{self.role} → {self.feature}"


class RoleCapability(models.Model):
    """Link table between roles and capabilities."""

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_capabilities")
    capability = models.ForeignKey(
        Capability,
        on_delete=models.CASCADE,
        related_name="capability_roles",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("role", "capability")
        ordering = ["role__ordering", "capability__name"]

    def __str__(self) -> str:
        return f"{self.role} → {self.capability}"
