from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.forms import CapabilityForm, FeatureForm, RoleForm
from accounts.models import Capability, Feature, Role
from main import permissions as permission_utils


class AccessControlMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Ensure only authorised users can manage roles, features, and capabilities.
    Superusers always pass; optionally a capability can be required.
    """

    login_url = "accounts:login"
    permission_denied_redirect = "main:unified_operations_dashboard"
    required_capability: str | None = "accounts.manage_access"
    raise_exception = False

    def test_func(self) -> bool:
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if self.required_capability:
            return permission_utils.user_has_capability(user, self.required_capability)
        return False

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(
            self.request,
            "You do not have permission to manage roles, features, or capabilities.",
        )
        return redirect(self.permission_denied_redirect)


class PermissionInvalidateMixin:
    """
    Clear cached permission snapshots whenever data changes and show success feedback.
    """

    success_message: str | None = None
    cancel_url_name: str | None = None

    def invalidate_permissions(self) -> None:
        permission_utils.invalidate_permissions_cache()

    def add_success_message(self) -> None:
        if self.success_message:
            messages.success(self.request, self.success_message)

    def get_cancel_url(self) -> str:
        if self.cancel_url_name:
            return reverse(self.cancel_url_name)
        if hasattr(self, "success_url") and self.success_url:
            return str(self.success_url)
        return reverse_lazy("accounts:role_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("cancel_url", self.get_cancel_url())
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        self.invalidate_permissions()
        self.add_success_message()
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        self.invalidate_permissions()
        self.add_success_message()
        return response


# ---------------------------------------------------------------------------
# Feature management
# ---------------------------------------------------------------------------


class FeatureListView(AccessControlMixin, ListView):
    model = Feature
    template_name = "accounts/access/feature_list.html"
    context_object_name = "features"
    ordering = ["ordering", "name"]

    def get_queryset(self):
        return Feature.objects.order_by("ordering", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Manage Features"
        return context


class FeatureCreateView(PermissionInvalidateMixin, AccessControlMixin, CreateView):
    model = Feature
    form_class = FeatureForm
    template_name = "accounts/access/feature_form.html"
    success_url = reverse_lazy("accounts:feature_list")
    success_message = "Feature created successfully."
    cancel_url_name = "accounts:feature_list"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Add Feature"
        return context


class FeatureUpdateView(PermissionInvalidateMixin, AccessControlMixin, UpdateView):
    model = Feature
    form_class = FeatureForm
    template_name = "accounts/access/feature_form.html"
    success_url = reverse_lazy("accounts:feature_list")
    success_message = "Feature updated successfully."
    cancel_url_name = "accounts:feature_list"
    slug_field = "key"
    slug_url_kwarg = "key"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit Feature: {self.object.name}"
        return context


class FeatureDeleteView(PermissionInvalidateMixin, AccessControlMixin, DeleteView):
    model = Feature
    template_name = "accounts/access/feature_confirm_delete.html"
    success_url = reverse_lazy("accounts:feature_list")
    success_message = "Feature deleted successfully."
    cancel_url_name = "accounts:feature_list"
    slug_field = "key"
    slug_url_kwarg = "key"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Delete Feature: {self.object.name}"
        return context


# ---------------------------------------------------------------------------
# Capability management
# ---------------------------------------------------------------------------


class CapabilityListView(AccessControlMixin, ListView):
    model = Capability
    template_name = "accounts/access/capability_list.html"
    context_object_name = "capabilities"
    ordering = ["category", "name"]

    def get_queryset(self):
        return Capability.objects.order_by("category", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Manage Capabilities"
        return context


class CapabilityCreateView(PermissionInvalidateMixin, AccessControlMixin, CreateView):
    model = Capability
    form_class = CapabilityForm
    template_name = "accounts/access/capability_form.html"
    success_url = reverse_lazy("accounts:capability_list")
    success_message = "Capability created successfully."
    cancel_url_name = "accounts:capability_list"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Add Capability"
        return context


class CapabilityUpdateView(PermissionInvalidateMixin, AccessControlMixin, UpdateView):
    model = Capability
    form_class = CapabilityForm
    template_name = "accounts/access/capability_form.html"
    success_url = reverse_lazy("accounts:capability_list")
    success_message = "Capability updated successfully."
    cancel_url_name = "accounts:capability_list"
    slug_field = "key"
    slug_url_kwarg = "key"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit Capability: {self.object.name}"
        return context


class CapabilityDeleteView(PermissionInvalidateMixin, AccessControlMixin, DeleteView):
    model = Capability
    template_name = "accounts/access/capability_confirm_delete.html"
    success_url = reverse_lazy("accounts:capability_list")
    success_message = "Capability deleted successfully."
    cancel_url_name = "accounts:capability_list"
    slug_field = "key"
    slug_url_kwarg = "key"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Delete Capability: {self.object.name}"
        return context


# ---------------------------------------------------------------------------
# Role management
# ---------------------------------------------------------------------------


class RoleListView(AccessControlMixin, ListView):
    model = Role
    template_name = "accounts/access/role_list.html"
    context_object_name = "roles"

    def get_queryset(self):
        return Role.objects.order_by("ordering", "name").prefetch_related("features", "capabilities")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Manage Roles"
        context["capability_labels"] = permission_utils.list_all_capabilities()
        return context


class RoleCreateView(PermissionInvalidateMixin, AccessControlMixin, CreateView):
    model = Role
    form_class = RoleForm
    template_name = "accounts/access/role_form.html"
    success_url = reverse_lazy("accounts:role_list")
    success_message = "Role created successfully."
    cancel_url_name = "accounts:role_list"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Add Role"
        return context


class RoleUpdateView(PermissionInvalidateMixin, AccessControlMixin, UpdateView):
    model = Role
    form_class = RoleForm
    template_name = "accounts/access/role_form.html"
    success_url = reverse_lazy("accounts:role_list")
    success_message = "Role updated successfully."
    cancel_url_name = "accounts:role_list"
    slug_field = "key"
    slug_url_kwarg = "key"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit Role: {self.object.name}"
        return context


class RoleDeleteView(PermissionInvalidateMixin, AccessControlMixin, DeleteView):
    model = Role
    template_name = "accounts/access/role_confirm_delete.html"
    success_url = reverse_lazy("accounts:role_list")
    success_message = "Role deleted successfully."
    cancel_url_name = "accounts:role_list"
    slug_field = "key"
    slug_url_kwarg = "key"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Delete Role: {self.object.name}"
        from main.models import UserProfile

        context["user_count"] = UserProfile.objects.filter(role=self.object.key).count()
        return context

