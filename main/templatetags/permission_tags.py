from django import template

from main.permissions import (
    get_role_label,
    role_has_capability,
    user_has_app_access,
    user_has_capability,
    user_has_feature,
)

register = template.Library()


@register.filter
def has_permission_for(user, feature_name: str):
    """
    Template filter to check if a user has permission for a specific feature.

    Usage in template::

        {% if request.user|has_permission_for:'yield_report' %}
            <a href="{% url 'main:yield_report' %}">Yield Report</a>
        {% endif %}
    """
    if not getattr(user, "is_authenticated", False):
        return False

    return user_has_feature(user, feature_name)


@register.filter
def has_capability(user, capability: str):
    """Return True if the user grants the provided capability."""
    return user_has_capability(user, capability)


@register.filter
def lacks_capability(user, capability: str):
    """Inverse of ``has_capability`` for template readability."""
    return not user_has_capability(user, capability)


@register.filter
def has_app_access(user, app_key: str):
    """Return True if the user has access to the specified application."""
    return user_has_app_access(user, app_key)


@register.filter(name="role_has_capability")
def role_has_capability_filter(role: str, capability: str):
    """
    Evaluate a capability against a raw role value.

    Useful when iterating over role strings in templates.
    """
    return role_has_capability(role, capability)


@register.filter
def role_label(role: str, default: str = ""):
    """Return the human readable label for the supplied role."""
    label = get_role_label(role)
    if label is None:
        return default
    return label
