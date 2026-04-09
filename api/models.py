"""
API Server Models
-----------------
Comprehensive models for secure API access control with:
- API key generation and management
- Table-level permissions
- Column-level restrictions
- Rate limiting and usage tracking
- Active token authentication
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets
import hashlib
import uuid
from datetime import timedelta


class APIUser(models.Model):
    """
    API User Management
    Represents an API consumer with credentials and permissions
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('revoked', 'Revoked'),
    ]
    
    ACCESS_LEVEL_CHOICES = [
        ('web_only', 'Web Access Only'),
        ('api_only', 'API Access Only'),
        ('both', 'Both Web and API Access'),
    ]
    
    # User identification
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_users')
    name = models.CharField(max_length=200, help_text='API user/application name')
    description = models.TextField(blank=True, help_text='Description of API usage purpose')
    
    # Access level control
    access_level = models.CharField(
        max_length=10, 
        choices=ACCESS_LEVEL_CHOICES, 
        default='both',
        help_text="Type of access granted to this user"
    )
    
    # Status and lifecycle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text='API access expiration date')
    
    # Rate limiting
    rate_limit_per_minute = models.IntegerField(default=60, help_text='Max requests per minute')
    rate_limit_per_hour = models.IntegerField(default=1000, help_text='Max requests per hour')
    rate_limit_per_day = models.IntegerField(default=10000, help_text='Max requests per day')
    
    # IP restrictions
    allowed_ips = models.TextField(blank=True, help_text='Comma-separated list of allowed IP addresses (leave empty for no restriction)')
    
    # Usage tracking
    total_requests = models.BigIntegerField(default=0)
    last_request_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'api_user'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    @property
    def is_active(self):
        """Check if API user is currently active"""
        if self.status != 'active':
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
    
    def check_ip_allowed(self, ip_address):
        """Check if IP address is allowed"""
        if not self.allowed_ips:
            return True
        allowed = [ip.strip() for ip in self.allowed_ips.split(',')]
        return ip_address in allowed
    
    def has_web_access(self):
        """Check if user has web access"""
        return self.access_level in ['web_only', 'both']
    
    def has_api_access(self):
        """Check if user has API access"""
        return self.access_level in ['api_only', 'both'] and self.is_active
    
    def get_user_accessible_sites(self):
        """Get sites accessible to this API user based on their main user profile"""
        try:
            user_profile = self.user.userprofile
            return user_profile.get_accessible_sites()
        except:
            # If no user profile exists, return empty queryset
            from main.models import AssetList
            return AssetList.objects.none()
    
    def get_user_accessible_countries(self):
        """Get countries accessible to this API user"""
        try:
            user_profile = self.user.userprofile
            return user_profile.get_accessible_countries()
        except:
            return []
    
    def get_user_accessible_portfolios(self):
        """Get portfolios accessible to this API user"""
        try:
            user_profile = self.user.userprofile
            return user_profile.get_accessible_portfolios()
        except:
            return []


class APIKey(models.Model):
    """
    API Key Management with secure token generation
    Each API user can have multiple keys for different purposes
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ]
    
    # Key identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    api_user = models.ForeignKey(APIUser, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=200, help_text='Key name/purpose')
    
    # Key data (hashed for security)
    key_prefix = models.CharField(max_length=10, unique=True, help_text='First 10 chars for identification')
    key_hash = models.CharField(max_length=128, unique=True, help_text='SHA-256 hash of the full key')
    
    # Status and lifecycle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Usage statistics
    total_requests = models.BigIntegerField(default=0)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional key metadata')
    
    class Meta:
        db_table = 'api_key'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['key_hash']),
            models.Index(fields=['key_prefix']),
            models.Index(fields=['api_user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"
    
    @staticmethod
    def generate_key():
        """Generate a secure random API key"""
        # Generate 32-byte random key (256 bits)
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_key(key):
        """Hash an API key using SHA-256"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @classmethod
    def create_key(cls, api_user, name, expires_in_days=None):
        """
        Create a new API key
        Returns tuple: (APIKey instance, plaintext_key)
        """
        plaintext_key = cls.generate_key()
        key_hash = cls.hash_key(plaintext_key)
        key_prefix = plaintext_key[:10]
        
        expires_at = None
        if expires_in_days:
            expires_at = timezone.now() + timedelta(days=expires_in_days)
        
        api_key = cls.objects.create(
            api_user=api_user,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            expires_at=expires_at
        )
        
        return api_key, plaintext_key
    
    @classmethod
    def verify_key(cls, plaintext_key):
        """
        Verify an API key and return the APIKey instance if valid
        Returns None if invalid
        """
        try:
            key_hash = cls.hash_key(plaintext_key)
            api_key = cls.objects.select_related('api_user').get(
                key_hash=key_hash,
                status='active'
            )
            
            # Check expiration
            if api_key.expires_at and timezone.now() > api_key.expires_at:
                api_key.status = 'expired'
                api_key.save()
                return None
            
            # Check if API user is active
            if not api_key.api_user.is_active:
                return None
            
            return api_key
        except cls.DoesNotExist:
            return None
    
    @property
    def is_active(self):
        """Check if key is currently active"""
        if self.status != 'active':
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class ActiveToken(models.Model):
    """
    Active Token Authentication
    Short-lived tokens for enhanced security against replay attacks
    """
    # Token identification
    token = models.CharField(max_length=128, unique=True, db_index=True)
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name='active_tokens')
    
    # Token lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Security tracking
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    request_count = models.IntegerField(default=0)
    
    # Token restrictions
    max_uses = models.IntegerField(default=100, help_text='Maximum number of times token can be used')
    is_revoked = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'api_active_token'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token', 'is_revoked']),
            models.Index(fields=['api_key', 'expires_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Token for {self.api_key.name} ({self.token[:10]}...)"
    
    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        return secrets.token_urlsafe(48)
    
    @classmethod
    def create_token(cls, api_key, ip_address, user_agent='', lifetime_minutes=60, max_uses=100):
        """
        Create a new active token
        """
        token = cls.generate_token()
        expires_at = timezone.now() + timedelta(minutes=lifetime_minutes)
        
        return cls.objects.create(
            token=token,
            api_key=api_key,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            max_uses=max_uses
        )
    
    @classmethod
    def verify_token(cls, token_string):
        """
        Verify a token and return the ActiveToken instance if valid
        """
        try:
            token = cls.objects.select_related('api_key__api_user').get(
                token=token_string,
                is_revoked=False
            )
            
            # Check expiration
            if timezone.now() > token.expires_at:
                return None
            
            # Check max uses
            if token.request_count >= token.max_uses:
                token.is_revoked = True
                token.save()
                return None
            
            # Check if API key is active
            if not token.api_key.is_active:
                return None
            
            return token
        except cls.DoesNotExist:
            return None
    
    @property
    def is_valid(self):
        """Check if token is currently valid"""
        if self.is_revoked:
            return False
        if timezone.now() > self.expires_at:
            return False
        if self.request_count >= self.max_uses:
            return False
        return True


class TablePermission(models.Model):
    """
    Table-level permissions for API access
    Controls which database tables are accessible via API
    """
    # Permission identification
    api_user = models.ForeignKey(APIUser, on_delete=models.CASCADE, related_name='table_permissions')
    table_name = models.CharField(max_length=200, help_text='Database table name')
    
    # Access control
    can_read = models.BooleanField(default=True)
    can_filter = models.BooleanField(default=True, help_text='Allow filtering records')
    can_aggregate = models.BooleanField(default=True, help_text='Allow aggregations (count, sum, etc.)')
    
    # Row limits
    max_records_per_request = models.IntegerField(default=1000, help_text='Maximum records per API request')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'api_table_permission'
        unique_together = ['api_user', 'table_name']
        ordering = ['table_name']
        indexes = [
            models.Index(fields=['api_user', 'table_name']),
        ]
    
    def __str__(self):
        return f"{self.api_user.name} -> {self.table_name}"


class ColumnRestriction(models.Model):
    """
    Column-level restrictions
    Control which columns are visible/hidden for each table permission
    """
    RESTRICTION_TYPE_CHOICES = [
        ('hidden', 'Hidden'),
        ('masked', 'Masked'),
    ]
    
    # Restriction identification
    table_permission = models.ForeignKey(TablePermission, on_delete=models.CASCADE, related_name='column_restrictions')
    column_name = models.CharField(max_length=200, help_text='Column name to restrict')
    
    # Restriction type
    restriction_type = models.CharField(
        max_length=20, 
        choices=RESTRICTION_TYPE_CHOICES, 
        default='hidden',
        help_text='hidden: exclude from results, masked: return as null/***'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'api_column_restriction'
        unique_together = ['table_permission', 'column_name']
        ordering = ['column_name']
        indexes = [
            models.Index(fields=['table_permission', 'column_name']),
        ]
    
    def __str__(self):
        return f"{self.table_permission.table_name}.{self.column_name} ({self.restriction_type})"


class APIRequestLog(models.Model):
    """
    API Request Logging
    Track all API requests for analytics, debugging, and security
    """
    # Request identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    api_key = models.ForeignKey(APIKey, on_delete=models.SET_NULL, null=True, related_name='request_logs')
    active_token = models.ForeignKey(ActiveToken, on_delete=models.SET_NULL, null=True, related_name='request_logs')
    
    # Request details
    endpoint = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # Request parameters
    query_params = models.JSONField(default=dict, blank=True)
    request_body = models.JSONField(default=dict, blank=True)
    
    # Response details
    status_code = models.IntegerField()
    response_time_ms = models.FloatField(help_text='Response time in milliseconds')
    response_size_bytes = models.IntegerField(default=0)
    records_returned = models.IntegerField(default=0, help_text='Number of records returned')
    
    # Error tracking
    error_message = models.TextField(blank=True)
    
    # Security flags
    is_suspicious = models.BooleanField(default=False)
    security_flags = models.JSONField(default=list, blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'api_request_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['api_key', 'timestamp']),
            models.Index(fields=['endpoint', 'timestamp']),
            models.Index(fields=['status_code', 'timestamp']),
            models.Index(fields=['is_suspicious']),
        ]
    
    def __str__(self):
        key_name = self.api_key.name if self.api_key else 'Unknown'
        return f"{key_name} - {self.method} {self.endpoint} - {self.status_code}"


class RateLimitTracker(models.Model):
    """
    Rate Limiting Tracker
    Track request counts for rate limiting enforcement
    """
    PERIOD_CHOICES = [
        ('minute', 'Per Minute'),
        ('hour', 'Per Hour'),
        ('day', 'Per Day'),
    ]
    
    # Tracking identification
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name='rate_limits')
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateTimeField()
    
    # Count
    request_count = models.IntegerField(default=0)
    
    # Metadata
    last_request_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'api_rate_limit_tracker'
        unique_together = ['api_key', 'period', 'period_start']
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['api_key', 'period', 'period_start']),
        ]
    
    def __str__(self):
        return f"{self.api_key.name} - {self.period} - {self.request_count} requests"


class FailedAuthAttempt(models.Model):
    """
    Failed API Authentication Attempts
    Track failed API authentication attempts for brute force protection
    """
    FAILURE_REASON_CHOICES = [
        ('invalid_key', 'Invalid API Key'),
        ('expired_key', 'Expired API Key'),
        ('revoked_key', 'Revoked API Key'),
        ('ip_blocked', 'IP Address Blocked'),
        ('rate_limited', 'Rate Limited'),
        ('suspicious_pattern', 'Suspicious Pattern Detected'),
    ]
    
    # Attempt details
    ip_address = models.GenericIPAddressField()
    attempted_key = models.CharField(max_length=100, blank=True, help_text='First 20 chars of attempted key')
    user_agent = models.TextField(blank=True)
    endpoint = models.CharField(max_length=200, default='/api/v1/auth/token')
    
    # Failure information
    failure_reason = models.CharField(max_length=50, choices=FAILURE_REASON_CHOICES)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'api_failed_auth_attempts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['failure_reason']),
        ]
    
    def __str__(self):
        return f"{self.ip_address} - {self.failure_reason} at {self.created_at}"


class BlockedAPIIP(models.Model):
    """
    Blocked API IP Addresses
    Track IPs that are blocked from API access due to brute force attempts
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('removed', 'Removed'),
    ]
    
    # IP information
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.CharField(max_length=200)
    failed_attempts = models.IntegerField(default=0)
    
    # Timestamps
    first_attempt_at = models.DateTimeField()
    blocked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text='Null = permanent block')
    unblocked_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'api_blocked_ips'
        ordering = ['-blocked_at']
        indexes = [
            models.Index(fields=['ip_address', 'status']),
            models.Index(fields=['status', 'expires_at']),
        ]
    
    def __str__(self):
        return f"{self.ip_address} - Blocked ({self.status})"
    
    def is_active(self):
        """Check if block is still active"""
        if self.status != 'active':
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            # Auto-expire the block
            self.status = 'expired'
            self.save()
            return False
        
        return True
