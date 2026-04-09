from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from main.models import AssetList, device_list
from ..models import LossCategory, Ticket, TicketCategory, TicketSubCategory
from ..utils import get_accessible_sites_for_user, get_user_display_name, log_ticket_activity

if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class TicketFormService:
    """Encapsulates ticket creation and update logic for React forms."""

    def __init__(self, user: User):
        self.user = user

    def get_form_options(self) -> Dict[str, Any]:
        """Returns available options for form fields."""
        accessible_sites = get_accessible_sites_for_user(self.user)
        users_queryset = User.objects.filter(is_active=True).order_by("username")

        return {
            "sites": [
                {"value": site.asset_code, "label": site.asset_name}
                for site in accessible_sites
            ],
            "categories": [
                {"value": str(cat.id), "label": cat.name}
                for cat in TicketCategory.objects.filter(is_active=True).order_by("display_order", "name")
            ],
            "subCategories": [
                {
                    "value": str(sub.id),
                    "label": sub.name,
                    "category": str(sub.category_id),
                }
                for sub in TicketSubCategory.objects.filter(is_active=True, category__is_active=True).order_by("category__display_order", "display_order", "name")
            ],
            "lossCategories": [
                {"value": str(cat.id), "label": cat.name}
                for cat in LossCategory.objects.filter(is_active=True).order_by("display_order", "name")
            ],
            "priorities": [
                {"value": value, "label": label}
                for value, label in Ticket.PRIORITY_CHOICES
            ],
            "users": [
                {"value": str(u.id), "label": get_user_display_name(u)}
                for u in users_queryset
            ],
        }

    def get_device_options(self, site_code: str, device_type: Optional[str] = None, subgroup: Optional[str] = None, location: Optional[str] = None) -> list[Dict[str, Any]]:
        """Returns devices available for a given site, optionally filtered by device_type, subgroup (for sub-devices), and location."""
        try:
            site = AssetList.objects.get(asset_code=site_code)
        except AssetList.DoesNotExist:
            return []

        from django.db.models import Q
        
        # If subgroup is provided, filter by device_sub_group (for sub-devices)
        # Sub-devices are devices where device_sub_group equals the selected device_id
        # Based on old implementation, sub-devices also have the same parent_code (site)
        # Note: Do NOT filter by device_type when loading sub-devices, as sub-devices
        # may have a different device_type than the parent device
        if subgroup:
            # Filter by both parent_code and device_sub_group (matching old API behavior exactly)
            # This matches the old api_views.py implementation - it doesn't filter by device_type
            # when subgroup is provided
            query = Q(parent_code=site.asset_code) & Q(device_sub_group=subgroup)
            # Also filter by location if provided (for sub-devices)
            if location:
                query &= Q(location=location)
            devices = device_list.objects.filter(query).order_by("device_name")
            
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Searching for sub-devices at site={site.asset_code} with device_sub_group={subgroup}, device_type={device_type}, location={location}")
            logger.info(f"Found {devices.count()} devices")
            
            # Log sample device_sub_group values for debugging
            sample_devices = device_list.objects.filter(
                parent_code=site.asset_code
            ).exclude(device_sub_group__isnull=True).exclude(device_sub_group='').values_list('device_sub_group', flat=True).distinct()[:20]
            logger.info(f"Sample device_sub_group values for site {site.asset_code}: {list(sample_devices)}")
            
            # Check if the selected device exists
            try:
                selected_device = device_list.objects.get(device_id=subgroup)
                logger.info(f"Selected device {subgroup} exists, device_sub_group='{selected_device.device_sub_group}'")
            except device_list.DoesNotExist:
                logger.warning(f"Selected device {subgroup} not found in database")
        else:
            # For main devices, filter by parent_code (site) and optionally device_type and location
            query = Q(parent_code=site.asset_code)
            if device_type:
                query &= Q(device_type=device_type)
            if location:
                query &= Q(location=location)
            devices = device_list.objects.filter(query).order_by("device_name")

        return [
            {
                "value": device.device_id,
                "label": device.device_name,
                "device_type": device.device_type,
                "device_sub_group": device.device_sub_group,
                "warranty_expire_date": device.equipment_warranty_expire_date.isoformat() if device.equipment_warranty_expire_date else None,
            }
            for device in devices
        ]

    def get_location_options(self, site_code: str) -> list[Dict[str, Any]]:
        """Returns unique locations available for a given site."""
        try:
            site = AssetList.objects.get(asset_code=site_code)
        except AssetList.DoesNotExist:
            return []

        # Get distinct locations for devices at this site
        locations = (
            device_list.objects
            .filter(parent_code=site.asset_code)
            .exclude(location__isnull=True)
            .exclude(location='')
            .values_list('location', flat=True)
            .distinct()
            .order_by('location')
        )

        return [
            {"value": location, "label": location}
            for location in locations
        ]

    @transaction.atomic
    def create_ticket(self, data: Dict[str, Any], ip_address: Optional[str] = None) -> Ticket:
        """Creates a new ticket from form data."""
        # Extract and validate site
        site_code = data.get("asset_code")
        if not site_code:
            raise ValidationError("Site selection is required.")
        try:
            site = AssetList.objects.get(asset_code=site_code)
        except AssetList.DoesNotExist:
            raise ValidationError("Selected site does not exist.")

        # Validate device if provided
        device_id_value = data.get("device_id")
        device = None
        if device_id_value:
            try:
                device = device_list.objects.get(device_id=device_id_value)
                # Validate device belongs to site
                if device.parent_code != site.asset_code:
                    raise ValidationError("Selected device does not belong to the selected site.")
            except device_list.DoesNotExist:
                raise ValidationError("Selected device does not exist.")

        # Validate category
        category_id = data.get("category")
        if not category_id:
            raise ValidationError("Category is required.")
        try:
            category = TicketCategory.objects.get(id=category_id, is_active=True)
        except TicketCategory.DoesNotExist:
            raise ValidationError("Selected category does not exist.")

        # Validate loss category if provided
        loss_category = None
        if data.get("loss_category"):
            try:
                loss_category = LossCategory.objects.get(id=data["loss_category"], is_active=True)
            except LossCategory.DoesNotExist:
                raise ValidationError("Selected loss category does not exist.")

        sub_category = None
        if data.get("sub_category"):
            try:
                sub_category = TicketSubCategory.objects.get(id=data["sub_category"], is_active=True)
            except TicketSubCategory.DoesNotExist:
                raise ValidationError("Selected sub-category does not exist.")
            if sub_category.category_id != category.id:
                raise ValidationError("Sub-category does not belong to the selected category.")

        # Validate assigned_to if provided
        assigned_to = None
        if data.get("assigned_to"):
            try:
                assigned_to = User.objects.get(id=data["assigned_to"], is_active=True)
            except User.DoesNotExist:
                raise ValidationError("Selected user does not exist.")

        # Build metadata
        metadata = {}
        if device:
            metadata["device_info"] = {
                "device_id": device.device_id,
                "device_name": device.device_name,
                "device_serial": device.device_serial,
                "device_make": device.device_make,
                "device_model": device.device_model,
                "device_type": device.device_type,
            }

        sub_device_id = data.get("sub_device_id")
        if sub_device_id:
            metadata["sub_device_id"] = sub_device_id
            try:
                sub_device = device_list.objects.get(device_id=sub_device_id)
                metadata["sub_device_info"] = {
                    "device_id": sub_device.device_id,
                    "device_name": sub_device.device_name,
                    "device_serial": sub_device.device_serial,
                    "device_make": sub_device.device_make,
                    "device_model": sub_device.device_model,
                    "device_type": sub_device.device_type,
                }
            except device_list.DoesNotExist:
                pass

        if sub_category:
            metadata["sub_category"] = sub_category.name

        # Store location in metadata
        location = data.get("location")
        if location:
            metadata["location"] = location

        # Create ticket
        ticket = Ticket.objects.create(
            title=data.get("title", "").strip(),
            description=data.get("description", "").strip(),
            asset_code=site,
            device_id=device,
            category=category,
            sub_category=sub_category,
            loss_category=loss_category,
            loss_value=data.get("loss_value") or None,
            priority=data.get("priority", "medium"),
            assigned_to=assigned_to,
            created_by=self.user,
            metadata=metadata if metadata else {},
        )

        # Set watchers
        watcher_ids = data.get("watchers", [])
        if watcher_ids:
            watchers = User.objects.filter(id__in=watcher_ids, is_active=True)
            ticket.watchers.set(watchers)

        # Log activity
        log_ticket_activity(
            ticket=ticket,
            user=self.user,
            action_type="created",
            ip_address=ip_address,
        )

        return ticket

    @transaction.atomic
    def update_ticket(self, ticket_id: UUID, data: Dict[str, Any], ip_address: Optional[str] = None) -> Ticket:
        """Updates an existing ticket from form data."""
        try:
            ticket = Ticket.objects.get(id=ticket_id, is_active=True)
        except Ticket.DoesNotExist:
            raise ValidationError("Ticket does not exist.")

        # Check permissions
        from ..utils import can_user_edit_ticket

        if not can_user_edit_ticket(self.user, ticket):
            raise ValidationError("You do not have permission to edit this ticket.")

        # Update fields
        if "title" in data:
            ticket.title = data["title"].strip()
        if "description" in data:
            ticket.description = data["description"].strip()
        if "priority" in data:
            ticket.priority = data["priority"]
        if "category" in data:
            old_category_id = str(ticket.category.id) if ticket.category else None
            new_category_id = data["category"]
            try:
                ticket.category = TicketCategory.objects.get(id=data["category"], is_active=True)
                # Reset sub_category if category changed
                if old_category_id != new_category_id:
                    ticket.sub_category = None
                    if ticket.metadata:
                        ticket.metadata.pop("sub_category", None)
            except TicketCategory.DoesNotExist:
                raise ValidationError("Selected category does not exist.")
        if "loss_category" in data:
            if data["loss_category"]:
                try:
                    ticket.loss_category = LossCategory.objects.get(id=data["loss_category"], is_active=True)
                except LossCategory.DoesNotExist:
                    raise ValidationError("Selected loss category does not exist.")
            else:
                ticket.loss_category = None
        if "loss_value" in data:
            ticket.loss_value = data["loss_value"] or None
        if "assigned_to" in data:
            if data["assigned_to"]:
                try:
                    ticket.assigned_to = User.objects.get(id=data["assigned_to"], is_active=True)
                except User.DoesNotExist:
                    raise ValidationError("Selected user does not exist.")
            else:
                ticket.assigned_to = None

        # Update device if provided
        if "device_id" in data:
            device_id_value = data["device_id"]
            if device_id_value:
                try:
                    device = device_list.objects.get(device_id=device_id_value)
                    # Validate device belongs to site
                    if device.parent_code != ticket.asset_code.asset_code:
                        raise ValidationError("Selected device does not belong to the selected site.")
                    ticket.device_id = device
                    # Update metadata
                    if not ticket.metadata:
                        ticket.metadata = {}
                    ticket.metadata["device_info"] = {
                        "device_id": device.device_id,
                        "device_name": device.device_name,
                        "device_serial": device.device_serial,
                        "device_make": device.device_make,
                        "device_model": device.device_model,
                        "device_type": device.device_type,
                    }
                except device_list.DoesNotExist:
                    raise ValidationError("Selected device does not exist.")
            else:
                ticket.device_id = None
                if ticket.metadata:
                    ticket.metadata.pop("device_info", None)

        # Update sub_category
        if "sub_category" in data:
            sub_category_value = data.get("sub_category")
            if sub_category_value:
                try:
                    sub_category_obj = TicketSubCategory.objects.get(id=sub_category_value, is_active=True)
                except TicketSubCategory.DoesNotExist:
                    raise ValidationError("Selected sub-category does not exist.")
                if ticket.category and sub_category_obj.category_id != ticket.category.id:
                    raise ValidationError("Sub-category does not belong to the selected category.")
                ticket.sub_category = sub_category_obj
                if not ticket.metadata:
                    ticket.metadata = {}
                ticket.metadata["sub_category"] = sub_category_obj.name
            else:
                ticket.sub_category = None
                if ticket.metadata:
                    ticket.metadata.pop("sub_category", None)

        # Update location in metadata
        if "location" in data:
            if not ticket.metadata:
                ticket.metadata = {}
            location = data.get("location")
            if location:
                ticket.metadata["location"] = location
            else:
                ticket.metadata.pop("location", None)

        # Update watchers
        if "watchers" in data:
            watcher_ids = data["watchers"]
            if watcher_ids:
                watchers = User.objects.filter(id__in=watcher_ids, is_active=True)
                ticket.watchers.set(watchers)
            else:
                ticket.watchers.clear()

        ticket.save()

        # Log activity
        log_ticket_activity(
            ticket=ticket,
            user=self.user,
            action_type="updated",
            ip_address=ip_address,
        )

        return ticket

