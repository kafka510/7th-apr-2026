"""
Real-Time IP Blocking System
Blocks malicious IPs immediately when suspicious activity is detected
Uses database for persistent storage and better logging
"""

import os
import sys
import subprocess
import shutil
import logging
import threading
import time
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from shared_app.utils.email_utils import build_email_subject

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('realtime_blocking.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RealTimeIPBlocker:
    """Real-time IP blocking system that responds immediately to threats"""
    
    def __init__(self):
        # Company IP ranges (protected from blocking)
        self.COMPANY_IP_RANGES = [
            '125.19.224.0/24',   # Your company range
            '152.57.32.0/24',    # Your company range  
            '152.57.40.0/24',    # Your company range
            '152.57.37.0/24',    # Your company range
            '223.185.132.0/24',  # Your company range
            '10.80.100.0/24',    # Your local network range
            '192.168.0.0/16',    # Private network range
            '172.16.0.0/12',     # Private network range
            '10.0.0.0/8',        # Private network range
        ]
        
        # Protected IPs that should NEVER be blocked at system level
        self.PROTECTED_IPS_SYSTEM_LEVEL = [
            '125.19.224.18',     # Protected company IP
            '47.247.169.94',     # Protected company IP
            '172.16.0.0/12',
            '172.25.32.1',       # Docker WSL gateway IP - all users appear as this IP
        ]
        
        # Known legitimate users
        self.LEGITIMATE_USERS = ['jagad', 'Mezhi', 'pm']
        
        # Blocking thresholds for immediate response
        self.IMMEDIATE_BLOCK_THRESHOLDS = {
            'high_risk_patterns': 1,        # Block immediately on high-risk patterns
            'malicious_user_agents': 1,     # Block immediately on malicious user agents
            'critical_exploits': 1,         # Block immediately on critical exploits
            'failed_logins_anonymous': 5,   # Block after 5 failed logins from anonymous IPs
            'failed_logins_company': 15,    # Block after 15 failed logins from company IPs
            'rate_limit_violations': 3,     # Block after 3 rate limit violations
        }
        
        # Cache for tracking activities per IP (for performance)
        self.activity_cache = {}
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        # Cache keys for shared cache across workers
        self.CACHE_KEY_BLOCKED_IPS = 'realtime_blocker:blocked_ips'
        self.CACHE_KEY_BLOCKED_USERS = 'realtime_blocker:blocked_users'
        self.CACHE_KEY_VERSION = 'realtime_blocker:cache_version'
        self.CACHE_TTL = 300  # 5 minutes TTL as fallback
        
        # In-memory cache (for fast access, synced with shared cache)
        self._blocked_ips = None
        self._blocked_users = None
        self._cache_version = None
        
        # Don't load from database on startup - use lazy loading instead
        # This prevents slow startup times
        
    def is_company_ip(self, ip_address):
        """Check if IP is in company range"""
        try:
            import ipaddress
            for ip_range in self.COMPANY_IP_RANGES:
                if ipaddress.ip_address(ip_address) in ipaddress.ip_network(ip_range):
                    return True
            return False
        except:
            # Fallback method
            company_prefixes = ['125.19.224', '152.57.32', '152.57.40', '152.57.37', '223.185.132']
            return any(ip_address.startswith(prefix) for prefix in company_prefixes)
    
    def block_ip_windows(self, ip_address, reason):
        """Block IP using Windows Firewall (immediate blocking)"""
        try:
            # Create a unique rule name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rule_name = f"AutoBlock_{ip_address}_{timestamp}"
            
            cmd = [
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                f'name={rule_name}',
                'dir=in',
                'action=block',
                f'remoteip={ip_address}',
                'protocol=any'
            ]
            
            # Run command with timeout
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.critical(f"BLOCKED IP {ip_address} at Windows Firewall level: {reason}")
                return True
            else:
                # Always return True for application-level blocking
                # Windows Firewall often fails due to permissions, but we can still block in application
                logger.warning(f"Cannot block IP {ip_address} at Windows Firewall level (returncode: {result.returncode}, stderr: '{result.stderr}'). Will block in application only.")
                return True
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout blocking IP {ip_address} at Windows Firewall level - will block in application only")
            return True  # Still block in application
        except Exception as e:
            logger.warning(f"Error blocking IP {ip_address} at Windows Firewall level: {str(e)} - will block in application only")
            return True  # Still block in application
    
    def iptables_rule_exists(self, ip_address):
        """Check if iptables rule already exists for the IP"""
        try:
            check_cmd = ['iptables', '-C', 'INPUT', '-s', ip_address, '-j', 'DROP']
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def block_ip_iptables(self, ip_address, reason):
        """Block IP using iptables (Linux) - with fallback for containers"""
        try:
            # Check if IP is in protected list - NEVER block these at system level
            if ip_address in self.PROTECTED_IPS_SYSTEM_LEVEL:
                logger.warning(f"IP {ip_address} is in protected list - blocking at application level only (not system level)")
                return True  # Block in application only
            
            if not shutil.which('iptables'):
                raise FileNotFoundError("iptables not found in system path")

            if self.iptables_rule_exists(ip_address):
                logger.info(f"IP {ip_address} is already blocked at iptables level.")
                return True

            cmd = ['sudo', '/sbin/iptables', '-A', 'INPUT', '-s', ip_address, '-j', 'DROP']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logger.critical(f"BLOCKED IP {ip_address} at iptables level: {reason}")
                return True
            else:
                logger.warning(f"Cannot block IP {ip_address} at iptables level (returncode: {result.returncode}, stderr: '{result.stderr}'). Will block in application only.")
                return True

        except FileNotFoundError:
            logger.warning(f"iptables not available - blocking IP {ip_address} in application only")
            return True
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout blocking IP {ip_address} at iptables level - will block in application only")
            return True
        except Exception as e:
            logger.warning(f"Error blocking IP {ip_address} at iptables level: {str(e)} - will block in application only")
            return True
    
    def record_activity(self, ip_address, activity_type, risk_level, details=None):
        """Record suspicious activity for an IP"""
        with self.lock:
            current_time = time.time()
            
            if ip_address not in self.activity_cache:
                self.activity_cache[ip_address] = []
            
            # Add new activity
            self.activity_cache[ip_address].append({
                'time': current_time,
                'type': activity_type,
                'risk_level': risk_level,
                'details': details
            })
            
            # Clean old activities (older than 1 hour)
            one_hour_ago = current_time - 3600
            self.activity_cache[ip_address] = [
                activity for activity in self.activity_cache[ip_address] 
                if activity['time'] > one_hour_ago
            ]
            
            # Check if IP should be blocked
            self.check_and_block_ip(ip_address)
    
    def check_and_block_ip(self, ip_address):
        """Check if IP should be blocked based on recent activity"""
        if ip_address in self._get_blocked_ips():
            return  # Already blocked
        
        if ip_address not in self.activity_cache:
            return
        
        activities = self.activity_cache[ip_address]
        is_company_ip = self.is_company_ip(ip_address)
        
        # Count different types of activities
        high_risk_patterns = len([a for a in activities if a['type'] == 'high_risk_pattern'])
        malicious_user_agents = len([a for a in activities if a['type'] == 'malicious_user_agent'])
        critical_exploits = len([a for a in activities if a['type'] == 'critical_exploit'])
        failed_logins = len([a for a in activities if a['type'] == 'failed_login'])
        rate_limit_violations = len([a for a in activities if a['type'] == 'rate_limit_violation'])
        
        should_block = False
        reason = ""
        
        # Immediate blocking for critical threats (regardless of IP type)
        if high_risk_patterns >= self.IMMEDIATE_BLOCK_THRESHOLDS['high_risk_patterns']:
            should_block = True
            reason = f"High-risk patterns detected: {high_risk_patterns}"
        
        elif malicious_user_agents >= self.IMMEDIATE_BLOCK_THRESHOLDS['malicious_user_agents']:
            should_block = True
            reason = f"Malicious user agents detected: {malicious_user_agents}"
        
        elif critical_exploits >= self.IMMEDIATE_BLOCK_THRESHOLDS['critical_exploits']:
            should_block = True
            reason = f"Critical exploits detected: {critical_exploits}"
        
        # Context-dependent blocking
        elif failed_logins > 0:
            threshold = (self.IMMEDIATE_BLOCK_THRESHOLDS['failed_logins_company'] 
                        if is_company_ip 
                        else self.IMMEDIATE_BLOCK_THRESHOLDS['failed_logins_anonymous'])
            
            if failed_logins >= threshold:
                should_block = True
                reason = f"Excessive failed logins: {failed_logins} (threshold: {threshold})"
        
        elif rate_limit_violations >= self.IMMEDIATE_BLOCK_THRESHOLDS['rate_limit_violations']:
            should_block = True
            reason = f"Rate limit violations: {rate_limit_violations}"
        
        # Block IP if criteria met
        if should_block:
            # Get activity details for logging
            activity_details = {
                'failed_attempts': failed_logins,
                'suspicious_activities': len(activities),
                'high_risk_patterns': high_risk_patterns,
                'malicious_user_agents': malicious_user_agents,
                'critical_exploits': critical_exploits,
                'rate_limit_violations': rate_limit_violations,
            }
            
            self.block_ip_immediately(
                ip_address, reason, is_company_ip, 
                activity_details=activity_details
            )
    
    def block_ip_immediately(self, ip_address, reason, is_company_ip, user=None, user_agent="", 
                            country="", city="", region="", activity_details=None):
        """Block IP immediately using appropriate method and database logging"""
        try:
            with transaction.atomic():
                # Check if IP is already blocked in database
                from main.models import BlockedIP, IPBlockingLog
                
                # Create or update BlockedIP record
                blocked_ip, created = BlockedIP.objects.get_or_create(
                    ip_address=ip_address,
                    defaults={
                        'reason': reason,
                        'description': f"Automatically blocked due to: {reason}",
                        'priority': 'high' if is_company_ip else 'critical',
                        'status': 'active',
                        'block_count': 1,
                        'last_seen': timezone.now(),
                        'metadata': {
                            'is_company_ip': is_company_ip,
                            'user_agent': user_agent,
                            'activity_details': activity_details or {}
                        }
                    }
                )
                
                if not created:
                    # Update existing record
                    blocked_ip.block_count += 1
                    blocked_ip.last_seen = timezone.now()
                    blocked_ip.status = 'active'
                    blocked_ip.save()
                
                # Create IPBlockingLog entry
                blocking_log = IPBlockingLog.objects.create(
                    ip_address=ip_address,
                    block_type='automatic',
                    block_reason=self._get_block_reason_from_activity(reason),
                    reason_details=reason,
                    user_agent=user_agent,
                    country=country,
                    city=city,
                    region=region,
                    failed_attempts=activity_details.get('failed_attempts', 0) if activity_details else 0,
                    suspicious_activities=activity_details.get('suspicious_activities', 0) if activity_details else 0,
                    metadata=activity_details or {}
                )
                
                # Log the blocking decision
                ip_type = "Company IP" if is_company_ip else "External IP"
                logger.critical(f"BLOCKING {ip_type} {ip_address}: {reason}")
                
                # Block using appropriate method
                success = False
                if sys.platform == "win32":
                    success = self.block_ip_windows(ip_address, reason)
                elif sys.platform == "linux":
                    success = self.block_ip_iptables(ip_address, reason)
                else:
                    # Unknown platform - just block in application
                    logger.warning(f"Unknown platform {sys.platform} - blocking IP {ip_address} in application only")
                    success = True
                
                # Invalidate cache to force reload after database changes
                self._invalidate_cache()
                
                # Log result
                if success:
                    logger.info(f"Successfully blocked IP {ip_address} (application level)")
                    # Send email alert for serious security threats
                    self._send_security_alert_email(ip_address, reason, activity_details)
                else:
                    logger.error(f"Failed to block IP {ip_address}")
                    # Update blocking log with failure
                    blocking_log.status = 'unblocked'
                    blocking_log.unblock_reason = "System blocking failed"
                    blocking_log.save()
                
                return success
                
        except Exception as e:
            logger.error(f"Error blocking IP {ip_address} in database: {str(e)}")
            # Invalidate cache to force reload
            self._invalidate_cache()
            logger.warning(f"Cache invalidated after blocking IP {ip_address}")
            return True
    
    def handle_suspicious_activity(self, ip_address, activity_type, risk_level, details=None, user=None):
        """Handle suspicious activity and potentially block IP"""
        # Skip if already blocked
        if ip_address in self._get_blocked_ips():
            return
        
        # Skip if it's a company IP with legitimate user (unless critical threat)
        if (self.is_company_ip(ip_address) and user and 
            user.username in self.LEGITIMATE_USERS and 
            risk_level not in ['critical', 'high']):
            logger.info(f"Protected company IP {ip_address} from blocking (user: {user.username})")
            return
        
        # Record activity
        self.record_activity(ip_address, activity_type, risk_level, details)
    
    def _load_from_database(self):
        """Load blocked IPs and users from database and cache them"""
        try:
            from main.models import BlockedIP, BlockedUser
            from django.db import connection
            
            # Check if database is available and tables exist
            if not connection.introspection.table_names():
                logger.debug("Database not available - initializing empty blocking sets")
                blocked_ips_set = set()
                blocked_users_set = set()
            else:
                # Load active blocked IPs from database
                blocked_ips = BlockedIP.objects.filter(status='active')
                blocked_ips_set = set(blocked_ips.values_list('ip_address', flat=True))
                
                # Load active blocked users from database
                blocked_users = BlockedUser.objects.filter(status='active')
                blocked_users_set = set(blocked_users.values_list('user__username', flat=True))
            
            # Store in shared cache (accessible by all workers)
            cache.set(self.CACHE_KEY_BLOCKED_IPS, blocked_ips_set, self.CACHE_TTL)
            cache.set(self.CACHE_KEY_BLOCKED_USERS, blocked_users_set, self.CACHE_TTL)
            
            # Update cache version to signal other workers
            cache_version = time.time()
            cache.set(self.CACHE_KEY_VERSION, cache_version, self.CACHE_TTL)
            
            # Update in-memory cache
            self._blocked_ips = blocked_ips_set
            self._blocked_users = blocked_users_set
            self._cache_version = cache_version
            
            logger.info(f"Loaded {len(blocked_ips_set)} blocked IPs and {len(blocked_users_set)} blocked users from database (cached)")
            
            return blocked_ips_set, blocked_users_set
            
        except Exception as e:
            logger.warning(f"Could not load from database: {e}")
            # Initialize empty sets as fallback
            empty_set = set()
            cache.set(self.CACHE_KEY_BLOCKED_IPS, empty_set, self.CACHE_TTL)
            cache.set(self.CACHE_KEY_BLOCKED_USERS, empty_set, self.CACHE_TTL)
            self._blocked_ips = empty_set
            self._blocked_users = empty_set
            return empty_set, empty_set
    
    def _get_blocked_ips(self):
        """Get blocked IPs from cache or load from database (lazy loading)"""
        # Check if we need to reload from cache
        current_cache_version = cache.get(self.CACHE_KEY_VERSION)
        
        # If cache version changed or we don't have in-memory cache, reload
        if (self._blocked_ips is None or 
            self._cache_version != current_cache_version or 
            current_cache_version is None):
            
            # Try to get from shared cache first
            cached_ips = cache.get(self.CACHE_KEY_BLOCKED_IPS)
            
            if cached_ips is not None:
                # Cache hit - use cached data
                self._blocked_ips = cached_ips
                self._cache_version = current_cache_version
            else:
                # Cache miss - load from database and cache it
                self._blocked_ips, _ = self._load_from_database()
        
        return self._blocked_ips
    
    def _get_blocked_users(self):
        """Get blocked users from cache or load from database (lazy loading)"""
        # Check if we need to reload from cache
        current_cache_version = cache.get(self.CACHE_KEY_VERSION)
        
        # If cache version changed or we don't have in-memory cache, reload
        if (self._blocked_users is None or 
            self._cache_version != current_cache_version or 
            current_cache_version is None):
            
            # Try to get from shared cache first
            cached_users = cache.get(self.CACHE_KEY_BLOCKED_USERS)
            
            if cached_users is not None:
                # Cache hit - use cached data
                self._blocked_users = cached_users
                self._cache_version = current_cache_version
            else:
                # Cache miss - load from database and cache it
                _, self._blocked_users = self._load_from_database()
        
        return self._blocked_users
    
    def _invalidate_cache(self):
        """Invalidate the cache to force reload on next access"""
        # Update cache version to signal all workers to reload
        cache_version = time.time()
        cache.set(self.CACHE_KEY_VERSION, cache_version, self.CACHE_TTL)
        
        # Clear in-memory cache
        self._blocked_ips = None
        self._blocked_users = None
        self._cache_version = None
        
        # Also clear the shared cache entries (they'll be repopulated on next access)
        cache.delete(self.CACHE_KEY_BLOCKED_IPS)
        cache.delete(self.CACHE_KEY_BLOCKED_USERS)
    
    def _get_block_reason_from_activity(self, reason):
        """Map activity reason to block reason choice"""
        reason_mapping = {
            'high_risk_pattern': 'high_risk_pattern',
            'malicious_user_agent': 'malicious_user_agent',
            'critical_exploit': 'critical_exploit',
            'failed_login': 'failed_logins',
            'rate_limit_violation': 'rate_limit_violation',
            'suspicious_activity': 'suspicious_activity',
        }
        
        for key, value in reason_mapping.items():
            if key in reason.lower():
                return value
        return 'other'
    
    def check_cache_reload_signal(self):
        """Check for cache reload signal and reload if necessary"""
        try:
            signal_file = "reload_cache_signal.txt"
            
            # Check if signal file exists
            if os.path.exists(signal_file):
                try:
                    # Read the timestamp from the signal file
                    with open(signal_file, 'r') as f:
                        signal_timestamp = float(f.read().strip())
                    
                    # Check if this is a new signal (hasn't been processed yet)
                    if not hasattr(self, '_last_signal_timestamp'):
                        self._last_signal_timestamp = 0
                    
                    if signal_timestamp > self._last_signal_timestamp:
                        logger.info(f"Cache reload signal detected (timestamp: {signal_timestamp})")
                        
                        # Reload cache from database
                        self.force_reload_cache()
                        
                        # Update the last processed timestamp
                        self._last_signal_timestamp = signal_timestamp
                        
                        # Delete the signal file to prevent repeated processing
                        os.remove(signal_file)
                        logger.info("Cache reload signal processed and file removed")
                        
                except (ValueError, IOError) as e:
                    logger.warning(f"Error processing cache reload signal file: {e}")
                    # Remove corrupted signal file
                    try:
                        os.remove(signal_file)
                    except:
                        pass
                        
        except Exception as e:
            logger.warning(f"Error checking cache reload signal: {str(e)}")
    
    def force_reload_cache(self):
        """Force reload of cache from database"""
        try:
            logger.info("Forcing cache reload from database...")
            
            # Store old cache sizes for logging
            old_ip_count = len(self._get_blocked_ips()) if self._blocked_ips is not None else 0
            old_user_count = len(self._get_blocked_users()) if self._blocked_users is not None else 0
            
            # Reload from database (this will update cache)
            new_blocked_ips, new_blocked_users = self._load_from_database()
            
            # Log the results
            new_ip_count = len(new_blocked_ips)
            new_user_count = len(new_blocked_users)
            
            logger.info(f"Cache reload complete: IPs {old_ip_count} → {new_ip_count}, Users {old_user_count} → {new_user_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during forced cache reload: {str(e)}")
            return False
    
    def is_ip_blocked(self, ip_address):
        """Check if IP is blocked (check cache and database)"""
        # NEVER block the protected gateway IP
        if ip_address == '172.25.32.1':
            return False
            
        # Check cached blocked IPs (lazy loaded)
        blocked_ips = self._get_blocked_ips()
        if ip_address in blocked_ips:
            return True
        
        # Double-check database for active blocks (in case cache is stale)
        try:
            from main.models import BlockedIP
            blocked_ip = BlockedIP.objects.filter(
                ip_address=ip_address, 
                status='active'
            ).first()
            
            if blocked_ip and blocked_ip.is_active:
                # IP is blocked but not in cache - invalidate cache to reload
                self._invalidate_cache()
                return True
            elif blocked_ip and not blocked_ip.is_active:
                # IP was unblocked - invalidate cache to reload
                self._invalidate_cache()
                return False
                
        except Exception as e:
            logger.warning(f"Error checking IP block status in database: {e}")
        
        return False
    
    def is_user_blocked(self, username):
        """Check if user is blocked (check cache and database)"""
        # Check cached blocked users (lazy loaded)
        blocked_users = self._get_blocked_users()
        if username in blocked_users:
            return True
        
        # Double-check database for active blocks (in case cache is stale)
        try:
            from main.models import BlockedUser
            blocked_user = BlockedUser.objects.filter(
                user__username=username, 
                status='active'
            ).first()
            
            if blocked_user and blocked_user.is_active:
                # User is blocked but not in cache - invalidate cache to reload
                self._invalidate_cache()
                return True
            elif blocked_user and not blocked_user.is_active:
                # User was unblocked - invalidate cache to reload
                self._invalidate_cache()
                return False
                
        except Exception as e:
            logger.warning(f"Error checking user block status in database: {e}")
        
        return False
    
    def get_blocking_stats(self):
        """Get current blocking statistics from database"""
        try:
            from main.models import BlockedIP, BlockedUser
            
            # Get stats from database
            active_blocked_ips = BlockedIP.objects.filter(status='active')
            active_blocked_users = BlockedUser.objects.filter(status='active')
            
            return {
                'total_blocked_ips': active_blocked_ips.count(),
                'blocked_ips': list(active_blocked_ips.values_list('ip_address', flat=True)),
                'total_blocked_users': active_blocked_users.count(),
                'blocked_users': list(active_blocked_users.values_list('user__username', flat=True)),
                'tracked_ips': len(self.activity_cache),
                'company_ips_protected': len([ip for ip in self.activity_cache.keys() if self.is_company_ip(ip)]),
                'recent_blocks_24h': BlockedIP.objects.filter(
                    created_at__gte=timezone.now() - timezone.timedelta(hours=24)
                ).count(),
            }
        except Exception as e:
            logger.error(f"Error getting blocking stats from database: {e}")
            # Fallback to memory stats
            blocked_ips = self._get_blocked_ips()
            blocked_users = self._get_blocked_users()
            return {
                'total_blocked_ips': len(blocked_ips),
                'blocked_ips': list(blocked_ips),
                'total_blocked_users': len(blocked_users),
                'blocked_users': list(blocked_users),
                'tracked_ips': len(self.activity_cache),
                'company_ips_protected': len([ip for ip in self.activity_cache.keys() if self.is_company_ip(ip)]),
            }
    
    def block_user_immediately(self, username, reason, ip_address="", user_agent="", 
                              country="", city="", activity_details=None):
        """Block user account immediately with database logging"""
        try:
            with transaction.atomic():
                from main.models import BlockedUser, UserBlockingLog
                from django.contrib.auth.models import User
                
                # Provide default IP address if none provided
                if not ip_address:
                    ip_address = "127.0.0.1"  # Default to localhost for manual blocks
                
                # Get user object
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    logger.error(f"User {username} not found for blocking")
                    return False
                
                # Create or update BlockedUser record
                blocked_user, created = BlockedUser.objects.get_or_create(
                    user=user,
                    defaults={
                        'reason': reason,
                        'description': f"Automatically blocked due to: {reason}",
                        'priority': 'high',
                        'status': 'active',
                        'block_count': 1,
                        'last_seen': timezone.now(),
                        'metadata': {
                            'ip_address': ip_address,
                            'user_agent': user_agent,
                            'activity_details': activity_details or {}
                        }
                    }
                )
                
                if not created:
                    # Update existing record
                    blocked_user.block_count += 1
                    blocked_user.last_seen = timezone.now()
                    blocked_user.status = 'active'
                    blocked_user.save()
                
                # Create UserBlockingLog entry
                blocking_log = UserBlockingLog.objects.create(
                    user=user,
                    block_type='automatic',
                    block_reason=self._get_user_block_reason_from_activity(reason),
                    reason_details=reason,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    country=country,
                    city=city,
                    failed_attempts=activity_details.get('failed_attempts', 0) if activity_details else 0,
                    suspicious_activities=activity_details.get('suspicious_activities', 0) if activity_details else 0,
                    metadata=activity_details or {}
                )
                
                # Invalidate cache to force reload
                self._invalidate_cache()
                
                # Disable the user account in Django
                user.is_active = False
                user.save()
                
                # Enhanced logging for blocking decision
                logger.critical(
                    f"BLOCKING USER {username}: {reason} | "
                    f"IP: {ip_address} | "
                    f"Block Type: automatic | "
                    f"Failed Attempts: {activity_details.get('failed_attempts', 0) if activity_details else 0} | "
                    f"Blocked User ID: {user.id} | "
                    f"Blocking Log ID: {blocking_log.id}"
                )
                logger.info(
                    f"User blocking completed: {username} | "
                    f"BlockedUser record: {'Created' if created else 'Updated'} | "
                    f"User account disabled: {not user.is_active} | "
                    f"Cache invalidated"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error blocking user {username} in database: {str(e)}")
            # Invalidate cache to force reload
            self._invalidate_cache()
            logger.warning(f"Cache invalidated after blocking user {username}")
            return True
    
    def _get_user_block_reason_from_activity(self, reason):
        """Map activity reason to user block reason choice"""
        reason_mapping = {
            'suspicious_activity': 'suspicious_activity',
            'failed_login': 'failed_logins',
            'security_violation': 'security_violation',
            'policy_violation': 'policy_violation',
            'account_compromise': 'account_compromise',
            'brute_force': 'brute_force',
            'malicious_behavior': 'malicious_behavior',
        }
        
        for key, value in reason_mapping.items():
            if key in reason.lower():
                return value
        return 'other'

    def _send_security_alert_email(self, ip_address, reason, activity_details=None):
        """Send email alert for serious security threats"""
        try:
            # Check if this is a critical threat worth emailing about
            reason_lower = reason.lower()
            is_critical = any(keyword in reason_lower for keyword in [
                'high_risk_pattern', 'malicious_user_agent', 'critical_exploit', 
                'sql injection', 'xss', 'command execution', 'directory traversal',
                'phpinfo', '.env', 'base64_decode', 'pearcmd', 'eval', 'exec'
            ])
            
            # Only send email for critical threats
            if not is_critical:
                return
            
            # Prepare email details
            subject = build_email_subject(
                f"🚨 CRITICAL SECURITY THREAT BLOCKED: {ip_address}"
            )
            
            # Format activity details
            details_text = ""
            if activity_details:
                details_text = f"""
Activity Details:
- Failed Attempts: {activity_details.get('failed_attempts', 0)}
- Suspicious Activities: {activity_details.get('suspicious_activities', 0)}
- High-Risk Patterns: {activity_details.get('high_risk_patterns', 0)}
- Malicious User Agents: {activity_details.get('malicious_user_agents', 0)}
- Critical Exploits: {activity_details.get('critical_exploits', 0)}
- Rate Limit Violations: {activity_details.get('rate_limit_violations', 0)}
"""
            
            message = f"""
SECURITY ALERT - CRITICAL THREAT BLOCKED

A critical security threat has been detected and blocked automatically.

Details:
- Blocked IP: {ip_address}
- Reason: {reason}
- Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
{details_text}
The IP address has been blocked automatically and access has been denied.

Action Required:
1. Review the blocking log in the admin panel
2. Check if this is a legitimate user (false positive)
3. Monitor for any related security events
4. If this is a false positive, manually unblock the IP in the admin panel

This is an automated alert from the Peak Pulse Security System.

Best regards,
Peak Pulse Security System
"""
            
            # Get recipient email from settings (default to jagadeshwar@peakenergy.asia)
            recipient_email = getattr(settings, 'SECURITY_ALERT_EMAIL', 'jagadeshwar@peakenergy.asia')
            
            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False
            )
            
            logger.info(f"Security alert email sent for IP {ip_address} to {recipient_email}")
            
        except Exception as e:
            logger.error(f"Failed to send security alert email for IP {ip_address}: {str(e)}")
    
    @property
    def blocked_ips(self):
        """
        Public read-only property to access blocked IPs set.
        Returns a copy of the set to prevent direct modification of the cache.
        To modify blocking, use database operations and then call _invalidate_cache().
        """
        return set(self._get_blocked_ips())  # Return a copy for security
    
    @property
    def blocked_users(self):
        """
        Public read-only property to access blocked users set.
        Returns a copy of the set to prevent direct modification of the cache.
        To modify blocking, use database operations and then call _invalidate_cache().
        """
        return set(self._get_blocked_users())  # Return a copy for security

# Global instance for use across the application
realtime_blocker = RealTimeIPBlocker()
