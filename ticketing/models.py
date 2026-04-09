from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class TicketCategory(models.Model):
    """Maintenance categories for tickets"""
    name = models.CharField(max_length=100, unique=True, help_text="Category name")
    description = models.TextField(blank=True, help_text="Category description")
    display_order = models.IntegerField(default=0, help_text="Display order in UI")
    is_active = models.BooleanField(default=True, help_text="Active status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teckting_ticketcategory'
        ordering = ['display_order', 'name']
        verbose_name = 'Ticket Category'
        verbose_name_plural = 'Ticket Categories'

    def __str__(self):
        return self.name


class LossCategory(models.Model):
    """Loss categorization for tickets"""
    name = models.CharField(max_length=100, unique=True, help_text="Loss category name")
    description = models.TextField(blank=True, help_text="Category description")
    display_order = models.IntegerField(default=0, help_text="Display order in UI")
    is_active = models.BooleanField(default=True, help_text="Active status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teckting_losscategory'
        ordering = ['display_order', 'name']
        verbose_name = 'Loss Category'
        verbose_name_plural = 'Loss Categories'

    def __str__(self):
        return self.name


class TicketSubCategory(models.Model):
    """Sub-categories that belong to a ticket category"""

    category = models.ForeignKey(
        TicketCategory,
        on_delete=models.PROTECT,
        related_name='subcategories',
        help_text="Parent category"
    )
    name = models.CharField(max_length=100, help_text="Sub-category name")
    description = models.TextField(blank=True, help_text="Sub-category description")
    display_order = models.IntegerField(default=0, help_text="Display order in UI")
    is_active = models.BooleanField(default=True, help_text="Active status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teckting_ticketsubcategory'
        ordering = ['display_order', 'name']
        unique_together = ('category', 'name')
        verbose_name = 'Ticket Sub-Category'
        verbose_name_plural = 'Ticket Sub-Categories'

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Ticket(models.Model):
    """Main ticket model for maintenance and loss-related issues"""
    
    STATUS_CHOICES = [
        ('raised', 'Raised'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('waiting_for_approval', 'Waiting for Approval'),
        ('closed', 'Closed'),
        ('reopened', 'Reopened'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=50, unique=True, db_index=True, help_text="Auto-generated ticket number")
    title = models.CharField(max_length=255, help_text="Ticket title/subject")
    description = models.TextField(help_text="Detailed description of the issue")
    
    # Relationships
    asset_code = models.ForeignKey(
        'main.AssetList', 
        on_delete=models.CASCADE,
        related_name='tickets',
        help_text="Related asset/site"
    )
    device_id = models.ForeignKey(
        'main.device_list',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        help_text="Related device (optional)"
    )
    
    # Status and categorization
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='raised',
        help_text="Current ticket status"
    )
    priority = models.CharField(
        max_length=10, 
        choices=PRIORITY_CHOICES, 
        default='medium',
        help_text="Priority level"
    )
    category = models.ForeignKey(
        TicketCategory, 
        on_delete=models.PROTECT,
        help_text="Maintenance category"
    )
    sub_category = models.ForeignKey(
        TicketSubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        help_text="Sub-category within the selected category"
    )
    loss_category = models.ForeignKey(
        LossCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Loss categorization (optional)"
    )
    loss_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Financial loss incurred due to this issue (in local currency)"
    )
    
    # User assignments
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_tickets',
        help_text="User who created the ticket"
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        help_text="User assigned to handle the ticket"
    )
    watchers = models.ManyToManyField(
        User,
        related_name='watched_tickets',
        blank=True,
        help_text="Users who can view and update this ticket (in addition to assigned user)"
    )
    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_tickets',
        help_text="User who closed the ticket"
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_tickets',
        help_text="User who last updated the ticket"
    )
    
    # Timestamps (all with timezone)
    created_at = models.DateTimeField(auto_now_add=True, help_text="Creation timestamp")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last update timestamp")
    closed_at = models.DateTimeField(null=True, blank=True, help_text="Closure timestamp")
    
    # Additional fields
    resolution_notes = models.TextField(blank=True, help_text="Resolution details")
    is_active = models.BooleanField(default=True, help_text="Soft delete flag")
    
    # Dynamic fields storage (JSON)
    metadata = models.JSONField(default=dict, blank=True, help_text="Dynamic fields storage including device info snapshot")

    class Meta:
        db_table = 'teckting_ticket'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket_number']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['asset_code', 'created_at']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['category', 'status']),
        ]
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'

    def __str__(self):
        return f"{self.ticket_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        super().save(*args, **kwargs)
    
    def generate_ticket_number(self):
        """Generate unique ticket number: TKT-YYYYMMDD-XXXX"""
        date_str = timezone.now().strftime('%Y%m%d')
        last_ticket = Ticket.objects.filter(
            ticket_number__startswith=f'TKT-{date_str}'
        ).order_by('-ticket_number').first()
        
        if last_ticket:
            try:
                last_num = int(last_ticket.ticket_number.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        
        return f'TKT-{date_str}-{new_num:04d}'
    
    @property
    def time_to_close(self):
        """Calculate time taken to close (if closed)"""
        if self.closed_at and self.created_at:
            return self.closed_at - self.created_at
        return None
    
    @property
    def days_since_creation(self):
        """Days since ticket creation"""
        return (timezone.now() - self.created_at).days
    
    @property
    def days_since_last_update(self):
        """Days since last update"""
        return (timezone.now() - self.updated_at).days


class TicketActivity(models.Model):
    """Track all ticket activities with timestamps and timezone"""
    
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('status_changed', 'Status Changed'),
        ('assigned', 'Assigned'),
        ('commented', 'Commented'),
        ('closed', 'Closed'),
        ('reopened', 'Reopened'),
        ('attachment_added', 'Attachment Added'),
        ('priority_changed', 'Priority Changed'),
        ('category_changed', 'Category Changed'),
        ('watchers_updated', 'Watchers Updated'),
        ('materials_updated', 'Materials Updated'),
        ('manpower_updated', 'Manpower Updated'),
    ]
    
    ticket = models.ForeignKey(
        Ticket, 
        on_delete=models.CASCADE, 
        related_name='activities',
        help_text="Related ticket"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        help_text="User who performed the action"
    )
    action_type = models.CharField(
        max_length=20, 
        choices=ACTION_CHOICES,
        help_text="Type of action performed"
    )
    old_value = models.JSONField(null=True, blank=True, help_text="Previous state/value")
    new_value = models.JSONField(null=True, blank=True, help_text="New state/value")
    field_changed = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text="Field that was changed"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Action timestamp (with timezone)"
    )
    notes = models.TextField(blank=True, help_text="Additional notes")
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="User IP address")

    class Meta:
        db_table = 'teckting_ticketactivity'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ticket', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action_type', 'timestamp']),
        ]
        verbose_name = 'Ticket Activity'
        verbose_name_plural = 'Ticket Activities'

    def __str__(self):
        return f"{self.ticket.ticket_number} - {self.get_action_type_display()} by {self.user.username}"


class TicketComment(models.Model):
    """Comments/notes on tickets"""
    
    ticket = models.ForeignKey(
        Ticket, 
        on_delete=models.CASCADE, 
        related_name='comments',
        help_text="Related ticket"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        help_text="Comment author"
    )
    comment = models.TextField(help_text="Comment text")
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal note (not visible to customer if applicable)"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Creation timestamp")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last update timestamp")

    class Meta:
        db_table = 'teckting_ticketcomment'
        ordering = ['created_at']
        verbose_name = 'Ticket Comment'
        verbose_name_plural = 'Ticket Comments'

    def __str__(self):
        return f"Comment on {self.ticket.ticket_number} by {self.user.username}"


class TicketAttachment(models.Model):
    """File attachments for tickets"""
    
    ticket = models.ForeignKey(
        Ticket, 
        on_delete=models.CASCADE, 
        related_name='attachments',
        help_text="Related ticket"
    )
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        help_text="User who uploaded the file"
    )
    file = models.FileField(upload_to='tickets/attachments/%Y/%m/%d/', help_text="Attached file")
    file_name = models.CharField(max_length=255, help_text="Original filename")
    file_size = models.IntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=50, help_text="MIME type")
    uploaded_at = models.DateTimeField(auto_now_add=True, help_text="Upload timestamp")

    class Meta:
        db_table = 'teckting_ticketattachment'
        ordering = ['-uploaded_at']
        verbose_name = 'Ticket Attachment'
        verbose_name_plural = 'Ticket Attachments'

    def __str__(self):
        return f"{self.file_name} - {self.ticket.ticket_number}"
    
    def save(self, *args, **kwargs):
        if self.file:
            if not self.file_name:
                self.file_name = self.file.name
            if not self.file_size:
                try:
                    self.file_size = self.file.size
                except:
                    pass
            # Ensure file_type is set
            if not self.file_type:
                try:
                    import mimetypes
                    file_type, _ = mimetypes.guess_type(self.file.name)
                    self.file_type = file_type or 'application/octet-stream'
                except:
                    self.file_type = 'application/octet-stream'
        super().save(*args, **kwargs)


class TicketMaterial(models.Model):
    """Materials used for resolving a ticket"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='materials',
        help_text="Associated ticket"
    )
    material_name = models.CharField(max_length=200, help_text="Name/description of the material")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantity used")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teckting_ticketmaterial'
        ordering = ['-created_at']
        verbose_name = 'Ticket Material'
        verbose_name_plural = 'Ticket Materials'

    def __str__(self):
        return f"{self.material_name} ({self.ticket.ticket_number})"


class TicketManpower(models.Model):
    """Manpower hours spent on a ticket"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='manpower_entries',
        help_text="Associated ticket"
    )
    person_name = models.CharField(max_length=200, help_text="Technician or personnel name")
    hours_worked = models.DecimalField(max_digits=10, decimal_places=2, help_text="Hours worked")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Hourly rate")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teckting_ticketmanpower'
        ordering = ['-created_at']
        verbose_name = 'Ticket Manpower Entry'
        verbose_name_plural = 'Ticket Manpower Entries'

    def __str__(self):
        return f"{self.person_name} ({self.ticket.ticket_number})"


class TicketFieldDefinition(models.Model):
    """Define dynamic fields that can be added without code changes"""
    
    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('textarea', 'Textarea'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('datetime', 'DateTime'),
        ('select', 'Select'),
        ('multiselect', 'Multi-Select'),
        ('checkbox', 'Checkbox'),
        ('file', 'File Upload'),
    ]
    
    field_name = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Field identifier (snake_case)"
    )
    field_label = models.CharField(
        max_length=200,
        help_text="Display label for the field"
    )
    field_type = models.CharField(
        max_length=20, 
        choices=FIELD_TYPE_CHOICES,
        help_text="Field input type"
    )
    field_options = models.JSONField(
        default=dict,
        help_text="Field-specific options (choices, validation, etc.)"
    )
    is_required = models.BooleanField(
        default=False,
        help_text="Whether field is required"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Sort order for display"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Active status"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'teckting_ticketfielddefinition'
        ordering = ['display_order', 'field_label']
        verbose_name = 'Ticket Field Definition'
        verbose_name_plural = 'Ticket Field Definitions'

    def __str__(self):
        return f"{self.field_label} ({self.field_type})"


class TicketEmailNotification(models.Model):
    """Email notification log for tickets"""
    
    NOTIFICATION_TYPE_CHOICES = [
        ('ticket_created', 'Ticket Created'),
        ('ticket_assigned', 'Ticket Assigned'),
        ('ticket_updated', 'Ticket Updated'),
        ('ticket_status_changed', 'Ticket Status Changed'),
        ('daily_reminder', 'Daily Reminder'),
        ('escalation', 'Escalation'),
        ('comment_added', 'Comment Added'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    ticket = models.ForeignKey(
        Ticket, 
        on_delete=models.CASCADE, 
        related_name='email_notifications',
        help_text="Related ticket"
    )
    recipient = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        help_text="Email recipient"
    )
    notification_type = models.CharField(
        max_length=25, 
        choices=NOTIFICATION_TYPE_CHOICES,
        help_text="Type of notification"
    )
    subject = models.CharField(max_length=255, help_text="Email subject")
    sent_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Sent timestamp"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Delivery status"
    )
    error_message = models.TextField(
        null=True, 
        blank=True,
        help_text="Error message if delivery failed"
    )

    class Meta:
        db_table = 'teckting_ticketemailnotification'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['ticket', 'sent_at']),
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['notification_type', 'sent_at']),
        ]
        verbose_name = 'Ticket Email Notification'
        verbose_name_plural = 'Ticket Email Notifications'

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.ticket.ticket_number} to {self.recipient.username}"


class PreventiveMaintenanceRule(models.Model):
    """Rules for automatic preventive maintenance ticket generation"""
    
    RULE_TYPE_CHOICES = [
        ('date_based', 'Date Based (Warranty/Expiry)'),
        ('frequency_based', 'Frequency Based (Recurring)'),
    ]
    
    FREQUENCY_UNIT_CHOICES = [
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
    ]
    
    name = models.CharField(max_length=255, help_text="Rule name (e.g., 'Equipment Warranty Check')")
    description = models.TextField(blank=True, help_text="Detailed description of the rule")
    rule_type = models.CharField(
        max_length=20,
        choices=RULE_TYPE_CHOICES,
        help_text="Type of preventive maintenance rule"
    )
    
    # For date-based rules
    date_field_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Device list field name for expiry date (e.g., 'equipment_warranty_expire_date')"
    )
    alert_days_before = models.IntegerField(
        default=30,
        help_text="Generate ticket X days before the date field"
    )
    
    # For frequency-based rules
    start_date_field = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Field name for start date (e.g., 'equipment_warranty_start_date' or use 'cod' for COD)"
    )
    frequency_field = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Device list field name containing frequency (e.g., 'calibration_frequency', 'pm_frequency')"
    )
    
    # Ticket settings
    category = models.ForeignKey(
        TicketCategory,
        on_delete=models.PROTECT,
        help_text="Ticket category for generated tickets"
    )
    priority = models.CharField(
        max_length=10,
        choices=Ticket.PRIORITY_CHOICES,
        default='medium',
        help_text="Priority for generated tickets"
    )
    title_template = models.CharField(
        max_length=255,
        help_text="Ticket title template (use {device_name}, {site_name}, {rule_name})"
    )
    description_template = models.TextField(
        help_text="Ticket description template (supports same placeholders)"
    )
    
    # Assignment - Role-based for site independence
    assign_to_role = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Auto-assign to users with this role (e.g., 'management', 'om', 'admin')"
    )
    send_email_notification = models.BooleanField(
        default=True,
        help_text="Send email notification when PM ticket is created"
    )
    
    # Settings
    is_active = models.BooleanField(default=True, help_text="Whether this rule is active")
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='pm_rules_created',
        help_text="User who created this rule"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teckting_pm_rule'
        ordering = ['name']
        verbose_name = 'Preventive Maintenance Rule'
        verbose_name_plural = 'Preventive Maintenance Rules'
    
    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"


class PreventiveMaintenanceSchedule(models.Model):
    """Track scheduled preventive maintenance for each device"""
    
    rule = models.ForeignKey(
        PreventiveMaintenanceRule,
        on_delete=models.CASCADE,
        related_name='schedules',
        help_text="Associated PM rule"
    )
    device = models.ForeignKey(
        'main.device_list',
        on_delete=models.CASCADE,
        related_name='pm_schedules',
        help_text="Device for this schedule"
    )
    asset = models.ForeignKey(
        'main.AssetList',
        on_delete=models.CASCADE,
        related_name='pm_schedules',
        help_text="Asset/site for this schedule"
    )
    
    # Scheduling information
    next_maintenance_date = models.DateField(
        help_text="Next scheduled maintenance date"
    )
    last_ticket_generated = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was the last ticket generated"
    )
    last_ticket = models.ForeignKey(
        Ticket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pm_schedule',
        help_text="Last generated ticket for this schedule"
    )
    last_completed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when last PM was completed (from ticket closure)"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teckting_pm_schedule'
        ordering = ['next_maintenance_date']
        verbose_name = 'PM Schedule'
        verbose_name_plural = 'PM Schedules'
        unique_together = ['rule', 'device']
    
    def __str__(self):
        return f"{self.device.device_name} - {self.rule.name} (Next: {self.next_maintenance_date})"
