"""
Centralised role and feature permission registry.

Role, feature, and capability information is primarily stored in the database
via the `accounts` app models. This module provides cached helper utilities
and falls back to legacy in-memory definitions when the database is not yet
available (for example during migrations or before initial data seeding).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

from django.apps import apps
from django.core.exceptions import AppRegistryNotReady
from django.db import DatabaseError
from django.db.models import Prefetch

ALL_FEATURES = "__all__"
ALL_CAPABILITIES = "__all__"

APP_BASE_CAPABILITIES: Dict[str, str] = {
    "web": "web.access",
    "ticketing": "ticketing.access_portal",
    "api": "api.access",
}

APP_ACCESS_LABELS: Dict[str, str] = {
    "web": "Web",
    "ticketing": "Ticketing",
    "api": "API",
}

CAPABILITY_APP_MAP: Dict[str, str] = {
    value: key for key, value in APP_BASE_CAPABILITIES.items()
}

# Broad mapping for capabilities that belong to a specific application
CAPABILITY_PREFIX_MAP: Dict[str, str] = {
    "ticketing.": "ticketing",
    "api.": "api",
    "web.": "web",
    "core.": "web",
    "user_management.": "web",
    "analytics.": "web",
    "data_upload.": "web",
    "data_api.": "web",
    "site_onboarding.": "web",
}

FEATURE_APP_OVERRIDES: Dict[str, str] = {
    "ticketing_ticket_list": "ticketing",
    "ticketing_my_tickets": "ticketing",
    "ticketing_ticket_create": "ticketing",
    "ticketing_ticket_dashboard": "ticketing",
    "ticketing_ticketing_admin": "ticketing",
    "ticketing_pm_rule_management": "ticketing",
}


# ---------------------------------------------------------------------------
# Legacy fallback definitions
# ---------------------------------------------------------------------------

# Define all available features/pages (matching URL names exactly)
FEATURES: Dict[str, str] = {
    "home": "Home",
    "dashboard": "Dashboard",
    "unified_operations_dashboard": "Unified Operations Dashboard",
    "portfolio_map": "Portfolio Map",
    "yield_report": "Yield Report",
    "yield_report_edited": "Yield Report (Edited)",
    "pr_gap": "PR Gap",
    "revenue_loss": "Revenue Loss",
    "areas_of_concern": "Areas of Concern (AOC)",
    "bess_performance": "BESS Performance",
    "bess_v1_performance": "BESS Dashboard",
    "minamata_typhoon_damage": "Minamata Typhoon Damage",
    "ic_budget_vs_expected": "IC Budget vs Expected",
    "main_dashboard": "Main Dashboard",
    "kpi_dashboard": "KPI Dashboard",
    "sales": "Sales",
    "generation_report": "Generation Report",
    "time_series_dashboard": "Time Series Dashboard",
    "analytics": "Analytics Dashboard",
    "user_management": "User Management",
    "data_upload": "Data Upload",
    "feedback_submit": "Submit Feedback",
    "feedback_list": "View Feedback (Admin)",
    "ticketing_ticket_list": "Ticket List",
    "ticketing_my_tickets": "My Tickets",
    "ticketing_ticket_create": "Create Ticket",
    "ticketing_ticket_dashboard": "Ticket Dashboard",
    "ticketing_ticketing_admin": "Ticketing Admin",
    "ticketing_pm_rule_management": "Preventive Maintenance Rules",
    "energy_revenue_hub": "Energy Revenue Hub",
    "engineering_tools": "Engineering Tools",
}


ROLE_DEFINITIONS: Dict[str, Dict[str, object]] = {
    "admin": {
        "label": "Admin",
        "description": "System administrator with unrestricted access.",
        "features": ALL_FEATURES,
        "capabilities": ALL_CAPABILITIES,
    },
    "asset_manager": {
        "label": "Asset Manager",
        "description": "Asset manager with broad operational visibility.",
        "features": [
            "home",
            "dashboard",
            "unified_operations_dashboard",
            "portfolio_map",
            "kpi_dashboard",
            "sales",
            "yield_report",
            "yield_report_edited",
            "pr_gap",
            "revenue_loss",
            "bess_performance",
            "main_dashboard",
            "generation_report",
            "feedback_submit",
        ],
        "capabilities": [
            "ticketing.assignable",
            "ticketing.view_operations",
            "ticketing.assign",
            "analytics.access",
        ],
    },
    "om": {
        "label": "O&M",
        "description": "Operations & Maintenance team member.",
        "features": [
            "home",
            "dashboard",
            "unified_operations_dashboard",
            "portfolio_map",
            "kpi_dashboard",
            "sales",
            "yield_report",
            "yield_report_edited",
            "pr_gap",
            "revenue_loss",
            "bess_performance",
            "main_dashboard",
            "generation_report",
            "feedback_submit",
        ],
        "capabilities": [
            "ticketing.assign",
            "ticketing.assignable",
            "ticketing.view_operations",
            "analytics.access",
        ],
    },
    "customer": {
        "label": "Customer",
        "description": "Customer stakeholder with limited dashboard visibility.",
        "features": [
            "home",
            "dashboard",
            "unified_operations_dashboard",
            "portfolio_map",
            "kpi_dashboard",
            "sales",
            "main_dashboard",
            "feedback_submit",
        ],
        "capabilities": [
            "ticketing.assignable",
        ],
    },
    "management": {
        "label": "Management",
        "description": "Management user with access to performance dashboards.",
        "features": [
            "home",
            "dashboard",
            "unified_operations_dashboard",
            "portfolio_map",
            "kpi_dashboard",
            "sales",
            "yield_report",
            "yield_report_edited",
            "pr_gap",
            "revenue_loss",
            "bess_performance",
            "main_dashboard",
            "generation_report",
            "feedback_submit",
        ],
        "capabilities": [
            "ticketing.assignable",
            "ticketing.view_operations",
            "analytics.access",
        ],
    },
    "others": {
        "label": "Others",
        "description": "Miscellaneous user with basic dashboard visibility.",
        "features": [
            "home",
            "dashboard",
            "unified_operations_dashboard",
            "portfolio_map",
            "main_dashboard",
            "feedback_submit",
        ],
        "capabilities": [],
    },
}

EXTRA_CAPABILITY_KEYS: Tuple[str, ...] = (
    "web.access",
    "api.access",
    "ticketing.access_portal",
    "ticketing.edit_any",
    "ticketing.close_any",
    "ticketing.manage_watchers",
    "ticketing.manage_settings",
    "ticketing.manage_pm_rules",
    "ticketing.view_all_sites",
    "ticketing.view_all_tickets",
    "data_upload.manage",
    "data_api.view_all",
    "user_management.manage",
    "api.manage",
    "site_onboarding.manage",
    "core.admin",
)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

_feature_snapshot_cache: Dict[str, str] | None = None
_capability_snapshot_cache: Dict[str, str] | None = None
_role_snapshot_cache: Dict[str, Dict[str, object]] | None = None
_feature_role_map_cache: Dict[str, Tuple[str, ...]] | None = None
_all_capabilities_cache: Tuple[str, ...] | None = None


def _ensure_iterable(value: object) -> Sequence[str]:
    if value in (None, "", [], (), set()):
        return ()
    if value in (ALL_FEATURES, ALL_CAPABILITIES):
        return (value,)  # sentinel
    if isinstance(value, (list, tuple, set)):
        return tuple(value)
    return (str(value),)


def _pretty_label(identifier: str) -> str:
    """Generate a human-readable label from a capability/feature key."""
    return identifier.replace(".", " ").replace("_", " ").title()


def _safe_get_model(app_label: str, model_name: str):
    """Return the model class if available, otherwise None."""
    try:
        return apps.get_model(app_label, model_name)
    except (LookupError, AppRegistryNotReady):
        return None


def _fallback_features() -> Dict[str, str]:
    return FEATURES.copy()


def _fallback_capabilities() -> Dict[str, str]:
    capability_labels: Dict[str, str] = {}
    for definition in ROLE_DEFINITIONS.values():
        for capability in _ensure_iterable(definition.get("capabilities")):
            if capability in (None, "", ALL_CAPABILITIES):
                continue
            capability_labels.setdefault(capability, _pretty_label(capability))
    for capability in EXTRA_CAPABILITY_KEYS:
        capability_labels.setdefault(capability, _pretty_label(capability))
    return capability_labels


def _fallback_role_snapshot() -> Dict[str, Dict[str, object]]:
    snapshot: Dict[str, Dict[str, object]] = {}
    for ordering, (role_key, definition) in enumerate(ROLE_DEFINITIONS.items()):
        snapshot[role_key] = {
            "label": definition.get("label", role_key),
            "description": definition.get("description", ""),
            "features": tuple(_ensure_iterable(definition.get("features"))),
            "capabilities": tuple(_ensure_iterable(definition.get("capabilities"))),
            "ordering": ordering,
            "is_active": True,
        }
    return snapshot


def _fetch_feature_snapshot() -> Dict[str, str]:
    global _feature_snapshot_cache
    if _feature_snapshot_cache is not None:
        return _feature_snapshot_cache

    feature_model = _safe_get_model("accounts", "Feature")
    if not feature_model:
        return _fallback_features()
    try:
        queryset = feature_model.objects.filter(is_active=True).order_by("ordering", "name")
        data = {feature.key: feature.name for feature in queryset}
        if data:
            _feature_snapshot_cache = data
            return _feature_snapshot_cache
    except DatabaseError:
        pass
    return _fallback_features()


def _fetch_capability_snapshot() -> Dict[str, str]:
    global _capability_snapshot_cache
    if _capability_snapshot_cache is not None:
        return _capability_snapshot_cache

    capability_model = _safe_get_model("accounts", "Capability")
    if not capability_model:
        return _fallback_capabilities()
    try:
        queryset = capability_model.objects.filter(is_active=True).order_by("category", "name")
        data = {cap.key: cap.name for cap in queryset}
        if data:
            _capability_snapshot_cache = data
            return _capability_snapshot_cache
    except DatabaseError:
        pass
    return _fallback_capabilities()


def _fetch_role_snapshot() -> Dict[str, Dict[str, object]]:
    global _role_snapshot_cache
    if _role_snapshot_cache is not None:
        return _role_snapshot_cache

    role_model = _safe_get_model("accounts", "Role")
    feature_model = _safe_get_model("accounts", "Feature")
    capability_model = _safe_get_model("accounts", "Capability")
    if not role_model or not feature_model or not capability_model:
        return _fallback_role_snapshot()

    roles_qs = (
        role_model.objects.filter(is_active=True)
        .prefetch_related(
            Prefetch(
                "features",
                queryset=feature_model.objects.filter(is_active=True).only("key"),
            ),
            Prefetch(
                "capabilities",
                queryset=capability_model.objects.filter(is_active=True).only("key"),
            ),
        )
        .order_by("ordering", "name")
    )

    try:
        roles = list(roles_qs)
    except DatabaseError:
        return _fallback_role_snapshot()

    snapshot: Dict[str, Dict[str, object]] = {}
    for index, role in enumerate(roles):
        try:
            feature_keys = tuple(role.features.values_list("key", flat=True))
            capability_keys = tuple(role.capabilities.values_list("key", flat=True))
        except DatabaseError:
            return _fallback_role_snapshot()
        snapshot[role.key] = {
            "label": role.name,
            "description": role.description,
            "features": feature_keys,
            "capabilities": capability_keys,
            "ordering": role.ordering if role.ordering is not None else index,
            "is_active": role.is_active,
        }

    if not snapshot:
        return _fallback_role_snapshot()
    _role_snapshot_cache = snapshot
    return _role_snapshot_cache


def invalidate_permissions_cache() -> None:
    """Clear cached permission snapshots."""
    global _feature_snapshot_cache
    global _capability_snapshot_cache
    global _role_snapshot_cache
    global _feature_role_map_cache
    global _all_capabilities_cache
    _feature_snapshot_cache = None
    _capability_snapshot_cache = None
    _role_snapshot_cache = None
    _feature_role_map_cache = None
    _all_capabilities_cache = None


def _get_user_profile(user):
    return getattr(user, "userprofile", None)


def user_has_app_access(user, app_key: str) -> bool:
    """
    Check if user has access to a specific app (web, ticketing, api).
    
    Args:
        user: Django user object
        app_key: App identifier ('web', 'ticketing', 'api')
    
    Returns:
        bool: True if user has access to the app, False otherwise
    """
    if not app_key:
        return True
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    profile = _get_user_profile(user)
    if not profile:
        return False
    # Use the has_app_access method if available (new system)
    if hasattr(profile, "has_app_access"):
        return profile.has_app_access(app_key)
    # Fallback to legacy checks for backward compatibility
    # But be strict - don't default to True for web
    if app_key == "ticketing":
        return getattr(profile, "ticketing_access", False)
    if app_key == "api":
        # Check if user has APIUser record
        try:
            from api.models import APIUser
            api_user = APIUser.objects.filter(user=user).first()
            return api_user is not None and api_user.access_level in ['api_only', 'both']
        except Exception:
            return False
    # For web access, check if user has web-related capabilities or features
    # Don't default to True - require explicit access
    if app_key == "web":
        # Check if user has any web-related capabilities
        # Import here to avoid circular import
        web_capabilities = ['web.access', 'core.admin', 'user_management.manage', 
                          'analytics.access', 'data_upload.manage']
        for cap in web_capabilities:
            if user_has_capability(user, cap):
                return True
        # Check if user has any web-related features (fallback)
        # This ensures users with web features get access even without explicit capabilities
        try:
            role_def = get_role_definition(getattr(profile, "role", None) or "")
            role_features = role_def.get("features", ())
            if role_features and role_features[0] == ALL_FEATURES:
                return True
            # Check for any web features
            web_features = ['portfolio_map', 'yield_report', 'kpi_dashboard', 'analytics', 
                          'user_management', 'data_upload', 'time_series_dashboard']
            for feature in web_features:
                if feature in role_features:
                    return True
        except Exception:
            pass
        # If no explicit web capability or feature, deny access
        return False
    return False


def _feature_app(feature: str) -> str:
    if feature in FEATURE_APP_OVERRIDES:
        return FEATURE_APP_OVERRIDES[feature]
    if feature.startswith("ticketing_"):
        return "ticketing"
    if feature.startswith("api_"):
        return "api"
    return "web"


def get_role_definition(role: str) -> Dict[str, object]:
    """Return the definition dictionary for the given role."""
    return _fetch_role_snapshot().get(role, {})


def get_role_label(role: str, default: str | None = None) -> str | None:
    """Return the human readable label for a role."""
    definition = get_role_definition(role)
    if not definition:
        return default
    return definition.get("label")  # type: ignore[return-value]


def get_role_choices(include_blank: bool = False, blank_label: str = "---------") -> List[Tuple[str, str]]:
    """
    Return Django-style choices for roles.

    Args:
        include_blank: If True, include an empty choice at the beginning.
        blank_label: Label to use for the empty choice.
    """
    choices = [(key, value["label"]) for key, value in _fetch_role_snapshot().items()]
    if include_blank:
        return [("", blank_label)] + choices
    return choices


def get_all_roles() -> Dict[str, str]:
    """Return all roles with their labels."""
    return {key: definition["label"] for key, definition in _fetch_role_snapshot().items()}


def get_all_features() -> Dict[str, str]:
    """Return all features with their labels."""
    return _fetch_feature_snapshot().copy()


def _role_features(role: str) -> Sequence[str]:
    definition = get_role_definition(role)
    features = tuple(definition.get("features", ()))
    if features and features[0] == ALL_FEATURES:
        return (ALL_FEATURES,)
    return features


def _role_capabilities(role: str) -> Sequence[str]:
    definition = get_role_definition(role)
    capabilities = tuple(definition.get("capabilities", ()))
    if capabilities and capabilities[0] == ALL_CAPABILITIES:
        return (ALL_CAPABILITIES,)
    return capabilities


def _all_capabilities() -> Tuple[str, ...]:
    global _all_capabilities_cache
    if _all_capabilities_cache is not None:
        return _all_capabilities_cache

    capability_keys = set()
    capability_snapshot = _fetch_capability_snapshot()
    for definition in _fetch_role_snapshot().values():
        capabilities = tuple(definition.get("capabilities", ()))
        if capabilities and capabilities[0] == ALL_CAPABILITIES:
            capability_keys.update(capability_snapshot.keys())
        else:
            capability_keys.update(capabilities)
    if not capability_keys:
        capability_keys.update(capability_snapshot.keys())
    _all_capabilities_cache = tuple(sorted(capability_keys))
    return _all_capabilities_cache


def list_all_capabilities() -> Tuple[str, ...]:
    """Return all explicit capability keys defined across roles."""
    return _all_capabilities()


def _feature_role_map() -> Dict[str, Tuple[str, ...]]:
    global _feature_role_map_cache
    if _feature_role_map_cache is not None:
        return _feature_role_map_cache

    features_snapshot = _fetch_feature_snapshot()
    mapping: Dict[str, List[str]] = {feature: [] for feature in features_snapshot}
    for role, definition in _fetch_role_snapshot().items():
        feature_keys = tuple(definition.get("features", ()))
        if feature_keys and feature_keys[0] == ALL_FEATURES:
            targets: Iterable[str] = features_snapshot.keys()
        else:
            targets = feature_keys
        for feature in targets:
            mapping.setdefault(feature, []).append(role)
    _feature_role_map_cache = {
        feature: tuple(sorted(set(roles))) for feature, roles in mapping.items()
    }
    return _feature_role_map_cache


def get_allowed_roles(feature: str) -> List[str]:
    """
    Get the list of roles allowed to access a specific feature.

    Args:
        feature: The feature name to check.
    """
    return list(_feature_role_map().get(feature, ()))


def has_permission(user_role: str | None, feature: str) -> bool:
    """
    Check if a user with the given role has permission to access a feature.

    Args:
        user_role: The user's role.
        feature: The feature to check access for.
    """
    if not user_role:
        return False
    allowed_roles = get_allowed_roles(feature)
    return user_role in allowed_roles


def get_user_permissions(user_role: str | None) -> Dict[str, str]:
    """
    Get all features that a user with the given role can access.

    Args:
        user_role: The user's role.
    """
    if not user_role:
        return {}
    features = {}
    for feature, label in _fetch_feature_snapshot().items():
        if has_permission(user_role, feature):
            features[feature] = label
    return features


def get_all_permissions() -> Dict[str, Tuple[str, ...]]:
    """
    Get the complete permissions matrix (feature -> roles).
    """
    return {feature: tuple(roles) for feature, roles in _feature_role_map().items()}


def role_has_capability(role: str | None, capability: str) -> bool:
    """
    Determine if the provided role grants the given capability.
    """
    if not role:
        return False
    capabilities = _role_capabilities(role)
    if not capabilities:
        return False
    if capabilities[0] == ALL_CAPABILITIES:
        return True
    return capability in capabilities


def get_roles_for_capability(capability: str) -> List[str]:
    """Return all roles that grant the specified capability."""
    roles: List[str] = []
    for role_key in _fetch_role_snapshot().keys():
        capabilities = _role_capabilities(role_key)
        if capabilities and capabilities[0] == ALL_CAPABILITIES:
            roles.append(role_key)
            continue
        if capability in capabilities:
            roles.append(role_key)
    return roles


def get_role_choices_for_capability(
    capability: str,
    *,
    include_blank: bool = False,
    blank_label: str = "---------",
) -> List[Tuple[str, str]]:
    """
    Return role choices limited to those granting the provided capability.
    """
    roles = get_roles_for_capability(capability)
    choices = [(role, get_role_label(role) or role) for role in roles]
    if include_blank:
        return [("", blank_label)] + choices
    return choices


def get_capabilities_for_role(role: str, *, expand_all: bool = False) -> Tuple[str, ...]:
    """
    Return capability keys for a role.

    Args:
        role: Role identifier.
        expand_all: When True, expand ALL_CAPABILITIES into concrete keys.
    """
    capabilities = _role_capabilities(role)
    if not capabilities:
        return ()
    if capabilities[0] == ALL_CAPABILITIES:
        if expand_all:
            return _all_capabilities()
        return (ALL_CAPABILITIES,)
    return tuple(sorted(set(capabilities)))


def user_has_capability(user, capability: str) -> bool:
    """
    Convenience wrapper to evaluate a capability for a Django user instance.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True

    app_key = CAPABILITY_APP_MAP.get(capability)
    if not app_key:
        for prefix, mapped_app in CAPABILITY_PREFIX_MAP.items():
            if capability.startswith(prefix):
                app_key = mapped_app
                break

    if app_key and not user_has_app_access(user, app_key):
        return False

    if capability in APP_BASE_CAPABILITIES.values():
        return user_has_app_access(user, app_key)

    user_profile = _get_user_profile(user)
    if not user_profile:
        return False
    role = getattr(user_profile, "role", None)
    return role_has_capability(role, capability)


def user_has_feature(user, feature: str) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True

    app_key = _feature_app(feature)
    if app_key and not user_has_app_access(user, app_key):
        return False

    user_profile = _get_user_profile(user)
    if not user_profile:
        return False
    return has_permission(getattr(user_profile, "role", None), feature)

