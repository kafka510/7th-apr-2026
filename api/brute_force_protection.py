"""
API Brute Force Protection
--------------------------
Comprehensive brute force protection for API authentication endpoints
Prevents unauthorized API key guessing and abuse
"""

from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import time
import logging

logger = logging.getLogger(__name__)


class APIBruteForceProtector:
    """Comprehensive brute force protection for API endpoints"""
    
    # === CONFIGURATION ===
    # Adjust these values based on your security requirements
    
    # MODERATE (Balanced) - RECOMMENDED
    MAX_ATTEMPTS_PER_IP = 5  # Block after 5 failed attempts
    ATTEMPT_WINDOW_MINUTES = 15  # Within 15 minutes
    BLOCK_DURATION_MINUTES = 60  # Block for 1 hour
    TOKEN_REQUEST_LIMIT = 10  # Max 10 token requests per minute per IP
    
    # Progressive delay (exponential backoff)
    ENABLE_PROGRESSIVE_DELAY = True
    
    def __init__(self):
        self.cache_prefix = 'api_bf_'
    
    def check_ip_allowed(self, ip_address):
        """
        Check if IP is allowed to make API authentication requests
        
        Returns: (allowed: bool, reason: str, retry_after: int)
        """
        # Check cache first (faster)
        cache_key = f"{self.cache_prefix}blocked_{ip_address}"
        cached_block = cache.get(cache_key)
        
        if cached_block:
            retry_after = cached_block.get('retry_after', 3600)
            return False, cached_block.get('reason', 'Too many failed attempts'), retry_after
        
        # Check database
        from .models import BlockedAPIIP
        try:
            blocked_ip = BlockedAPIIP.objects.get(ip_address=ip_address, status='active')
            
            if blocked_ip.is_active():
                # Calculate retry_after
                if blocked_ip.expires_at:
                    retry_after = int((blocked_ip.expires_at - timezone.now()).total_seconds())
                else:
                    retry_after = None  # Permanent block
                
                # Cache the block for faster future checks
                cache.set(cache_key, {
                    'reason': blocked_ip.reason,
                    'retry_after': retry_after or 86400  # 24 hours default
                }, timeout=300)  # Cache for 5 minutes
                
                return False, blocked_ip.reason, retry_after
        except BlockedAPIIP.DoesNotExist:
            pass
        
        return True, None, 0
    
    def record_failed_attempt(self, ip_address, attempted_key, failure_reason, user_agent='', endpoint='/api/v1/auth/token'):
        """
        Record a failed authentication attempt and check if IP should be blocked
        
        Returns: (should_block: bool, attempts_count: int, info: int)
            - should_block: Whether IP should be blocked now
            - attempts_count: Number of recent failed attempts
            - info: If should_block=True, retry_after seconds; else attempts_remaining
        """
        from .models import FailedAuthAttempt, BlockedAPIIP
        
        # Record the attempt
        FailedAuthAttempt.objects.create(
            ip_address=ip_address,
            attempted_key=attempted_key[:20] if attempted_key else '',  # Only store first 20 chars
            user_agent=user_agent[:500] if user_agent else '',
            endpoint=endpoint,
            failure_reason=failure_reason
        )
        
        # Count recent failed attempts from this IP
        window_start = timezone.now() - timedelta(minutes=self.ATTEMPT_WINDOW_MINUTES)
        recent_attempts = FailedAuthAttempt.objects.filter(
            ip_address=ip_address,
            created_at__gte=window_start
        ).count()
        
        logger.warning(f"Failed API auth attempt from {ip_address}: {failure_reason} ({recent_attempts}/{self.MAX_ATTEMPTS_PER_IP} attempts)")
        
        # Check if should block
        if recent_attempts >= self.MAX_ATTEMPTS_PER_IP:
            # Block the IP
            first_attempt = FailedAuthAttempt.objects.filter(
                ip_address=ip_address,
                created_at__gte=window_start
            ).order_by('created_at').first()
            
            expires_at = timezone.now() + timedelta(minutes=self.BLOCK_DURATION_MINUTES)
            
            blocked_ip, created = BlockedAPIIP.objects.get_or_create(
                ip_address=ip_address,
                defaults={
                    'reason': f'Brute force: {recent_attempts} failed attempts in {self.ATTEMPT_WINDOW_MINUTES} minutes',
                    'failed_attempts': recent_attempts,
                    'first_attempt_at': first_attempt.created_at if first_attempt else timezone.now(),
                    'expires_at': expires_at,
                    'status': 'active'
                }
            )
            
            if not created:
                # Update existing block
                blocked_ip.failed_attempts = recent_attempts
                blocked_ip.expires_at = expires_at
                blocked_ip.status = 'active'
                blocked_ip.save()
            
            # Cache the block
            cache_key = f"{self.cache_prefix}blocked_{ip_address}"
            cache.set(cache_key, {
                'reason': blocked_ip.reason,
                'retry_after': self.BLOCK_DURATION_MINUTES * 60
            }, timeout=self.BLOCK_DURATION_MINUTES * 60)
            
            # Integrate with main security system
            self._trigger_realtime_blocker(ip_address, recent_attempts)
            
            logger.critical(f"🚨 BLOCKED API access from {ip_address} due to {recent_attempts} failed attempts")
            
            return True, recent_attempts, self.BLOCK_DURATION_MINUTES * 60
        
        # Not blocked yet, but return attempt count
        attempts_remaining = self.MAX_ATTEMPTS_PER_IP - recent_attempts
        return False, recent_attempts, attempts_remaining
    
    def apply_progressive_delay(self, ip_address):
        """
        Apply exponential backoff delay based on recent failed attempts
        
        Returns: delay_seconds (float)
        """
        if not self.ENABLE_PROGRESSIVE_DELAY:
            return 0
        
        # Count recent attempts
        window_start = timezone.now() - timedelta(minutes=self.ATTEMPT_WINDOW_MINUTES)
        from .models import FailedAuthAttempt
        
        recent_attempts = FailedAuthAttempt.objects.filter(
            ip_address=ip_address,
            created_at__gte=window_start
        ).count()
        
        if recent_attempts == 0:
            return 0
        
        # Exponential backoff: 2^(attempts-1) seconds
        # 1st: 0s, 2nd: 1s, 3rd: 2s, 4th: 4s, 5th: 8s
        delay = min(2 ** (recent_attempts - 1), 16)  # Max 16 seconds
        
        if delay > 0:
            logger.info(f"Applying {delay}s progressive delay for {ip_address} (attempt #{recent_attempts})")
            time.sleep(delay)
        
        return delay
    
    def check_token_request_rate_limit(self, ip_address):
        """
        Check rate limit for token requests (independent of authentication success)
        
        Returns: (allowed: bool, retry_after: int)
        """
        cache_key = f"{self.cache_prefix}token_rate_{ip_address}"
        current_time = time.time()
        
        # Get request times from cache
        request_times = cache.get(cache_key, [])
        
        # Remove requests older than 1 minute
        request_times = [t for t in request_times if current_time - t < 60]
        
        # Check if limit exceeded
        if len(request_times) >= self.TOKEN_REQUEST_LIMIT:
            oldest_request = min(request_times)
            retry_after = int(60 - (current_time - oldest_request))
            logger.warning(f"Token request rate limit exceeded for {ip_address}")
            return False, retry_after
        
        # Add current request
        request_times.append(current_time)
        cache.set(cache_key, request_times, timeout=60)
        
        return True, 0
    
    def _trigger_realtime_blocker(self, ip_address, failed_attempts):
        """
        Trigger the main app's real-time IP blocker for severe violations
        """
        try:
            from main.middleware.realtime_ip_blocker import realtime_blocker
            
            # If severe brute force (5+ attempts), trigger permanent block
            if failed_attempts >= 5:
                realtime_blocker.block_ip_immediately(
                    ip_address,
                    f"API brute force attack: {failed_attempts} failed authentication attempts"
                )
                logger.critical(f"🛡️ Triggered real-time blocker for {ip_address}")
        except Exception as e:
            logger.error(f"Failed to trigger real-time blocker: {e}")
    
    def is_ip_suspicious(self, ip_address):
        """
        Check if IP has suspicious activity patterns
        
        Returns: (is_suspicious: bool, reason: str)
        """
        from .models import FailedAuthAttempt
        
        # Check for multiple different attempted keys (key guessing)
        window_start = timezone.now() - timedelta(minutes=5)
        recent_attempts = FailedAuthAttempt.objects.filter(
            ip_address=ip_address,
            created_at__gte=window_start
        )
        
        unique_keys = recent_attempts.values('attempted_key').distinct().count()
        
        if unique_keys > 3:  # Trying multiple different keys
            return True, f"Attempting multiple API keys ({unique_keys} different keys)"
        
        return False, None
    
    def get_ip_stats(self, ip_address):
        """Get statistics about an IP's authentication attempts"""
        from .models import FailedAuthAttempt, BlockedAPIIP
        
        window_start = timezone.now() - timedelta(minutes=self.ATTEMPT_WINDOW_MINUTES)
        recent_attempts = FailedAuthAttempt.objects.filter(
            ip_address=ip_address,
            created_at__gte=window_start
        ).count()
        
        total_attempts = FailedAuthAttempt.objects.filter(ip_address=ip_address).count()
        
        try:
            blocked = BlockedAPIIP.objects.get(ip_address=ip_address, status='active')
            is_blocked = blocked.is_active()
        except BlockedAPIIP.DoesNotExist:
            is_blocked = False
        
        return {
            'recent_attempts': recent_attempts,
            'total_attempts': total_attempts,
            'is_blocked': is_blocked,
            'attempts_remaining': max(0, self.MAX_ATTEMPTS_PER_IP - recent_attempts)
        }
    
    def cleanup_old_attempts(self, days=30):
        """Clean up old failed attempt records"""
        from .models import FailedAuthAttempt
        
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count = FailedAuthAttempt.objects.filter(created_at__lt=cutoff_date).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old failed auth attempts")
        return deleted_count
    
    def unblock_ip(self, ip_address, notes=''):
        """Manually unblock an IP address"""
        from .models import BlockedAPIIP
        
        try:
            blocked_ip = BlockedAPIIP.objects.get(ip_address=ip_address, status='active')
            blocked_ip.status = 'removed'
            blocked_ip.unblocked_at = timezone.now()
            if notes:
                blocked_ip.notes = notes
            blocked_ip.save()
            
            # Clear cache
            cache_key = f"{self.cache_prefix}blocked_{ip_address}"
            cache.delete(cache_key)
            
            logger.info(f"Manually unblocked IP: {ip_address}")
            return True, "IP unblocked successfully"
        except BlockedAPIIP.DoesNotExist:
            return False, "IP not found in block list"


# Global instance
brute_force_protector = APIBruteForceProtector()

