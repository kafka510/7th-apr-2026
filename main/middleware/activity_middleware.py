"""
Activity Logging and Security Monitoring Middleware

This middleware automatically logs all user activities and monitors for suspicious behavior.
"""

import time
import json
import re
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.http import JsonResponse
import logging
import time
import json
import re
from datetime import timedelta

from main.utils.connection_ip import extract_connection_ips

# Import models with error handling
try:
    from main.models import UserActivityLog, ActiveUserSession, SecurityAlert
except ImportError as e:
    # Handle case where models haven't been migrated yet
    print(f"Warning: Could not import activity models: {e}")
    UserActivityLog = None
    ActiveUserSession = None
    SecurityAlert = None

logger = logging.getLogger(__name__)


class ActivityLoggingMiddleware(MiddlewareMixin):
    """Middleware to log user activities and detect suspicious behavior"""
    
    # Patterns for detecting suspicious requests
    SUSPICIOUS_PATTERNS = [
        r'union.*select',  # SQL injection
        r'<script.*?>',    # XSS
        r'javascript:',    # XSS
        r'eval\(',         # Code injection
        r'base64_decode',  # Potential payload
        r'\.\./',          # Directory traversal
        r'etc/passwd',     # File access attempt
        r'cmd\.exe',       # Command execution
        r'wget|curl',      # Download attempts
    ]
    
    # Known malicious user agents
    MALICIOUS_USER_AGENTS = [
        'sqlmap',
        'nmap',
        'nikto',
        'dirb',
        'gobuster',
        'burpsuite',
        'owasp',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming request"""
        request._start_time = time.time()
        
        ips = extract_connection_ips(request)
        request._connection_ips = ips
        request._client_ip = ips["client_ip"]
        
        # Update or create active session for authenticated users
        if hasattr(request, 'user') and request.user.is_authenticated:
            self.update_active_session(request)
        
        return None
    
    def process_response(self, request, response):
        """Process response and log activity"""
        # Skip if models aren't available (not migrated yet)
        if not UserActivityLog:
            return response
            
        try:
            # Calculate response time
            start_time = getattr(request, '_start_time', time.time())
            response_time = time.time() - start_time
            
            # Get request details
            ips = getattr(request, "_connection_ips", None) or extract_connection_ips(request)
            ip_address = ips["client_ip"]
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:1000]  # Limit length
            method = request.method
            path = request.path
            status_code = response.status_code
            
            # Determine action type
            action = self.determine_action(request, response)
            
            # Get request data (safely)
            request_data = self.get_safe_request_data(request)
            
            # Analyze for suspicious activity
            is_suspicious, security_flags, risk_level = self.analyze_security(request, response)
            
            # Get geolocation (basic implementation - you might want to use a service)
            country, city, region = self.get_location_info(ip_address)
            
            # Get session key safely (handle anonymous requests)
            session_key = None
            if hasattr(request, 'session'):
                if request.session.session_key:
                    session_key = request.session.session_key
                elif hasattr(request, 'user') and request.user.is_authenticated:
                    # Only create session for authenticated users
                    try:
                        request.session.create()
                        session_key = request.session.session_key
                    except:
                        session_key = None
            
            # For anonymous requests, session_key will be None (which is allowed now)
            
            # Log the activity
            activity_log = UserActivityLog.objects.create(
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                session_key=session_key,
                peer_ip=ips["peer_ip"],
                forwarded_for=ips["forwarded_for"],
                client_ip=ips["client_ip"],
                ip_address=ip_address,
                user_agent=user_agent,
                action=action,
                resource=path,
                method=method,
                status_code=status_code,
                response_time=response_time,
                country=country,
                city=city,
                region=region,
                request_data=request_data,
                response_size=len(response.content) if hasattr(response, 'content') else 0,
                is_suspicious=is_suspicious,
                risk_level=risk_level,
                security_flags=security_flags,
            )
            
            # Create security alert if suspicious
            if is_suspicious and risk_level in ['high', 'critical']:
                self.create_security_alert(request, activity_log, security_flags, risk_level)
                
                # Trigger real-time blocking for critical threats
                if risk_level == 'critical':
                    self.trigger_realtime_blocking(request, activity_log, security_flags)
                
        except Exception as e:
            logger.error(f"Error in ActivityLoggingMiddleware: {str(e)}")
        
        return response
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
    
    def update_active_session(self, request):
        """Update or create active user session"""
        # Skip if models aren't available
        if not ActiveUserSession:
            return
            
        try:
            if not request.session.session_key:
                request.session.create()
            
            # Get location info for session
            ip_address = self.get_client_ip(request)
            country, city, region = self.get_location_info(ip_address)
            
            session, created = ActiveUserSession.objects.get_or_create(
                session_key=request.session.session_key,
                defaults={
                    'user': request.user,
                    'ip_address': ip_address,
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:1000],
                    'is_active': True,
                    'country': country,
                    'city': city,
                }
            )
            
            if not created:
                # Update existing session
                session.user = request.user
                session.ip_address = ip_address
                session.user_agent = request.META.get('HTTP_USER_AGENT', '')[:1000]
                session.is_active = True
                session.country = country
                session.city = city
                session.save(update_fields=['user', 'ip_address', 'user_agent', 'is_active', 'last_activity', 'country', 'city'])
                
        except Exception as e:
            logger.error(f"Error updating active session: {str(e)}")
    
    def determine_action(self, request, response):
        """Determine the type of action based on request and response"""
        method = request.method.upper()
        path = request.path.lower()
        status_code = response.status_code
        
        # Check for login/logout
        if 'login' in path:
            return 'failed_login' if status_code >= 400 else 'login'
        elif 'logout' in path:
            return 'logout'
        elif 'password' in path and 'reset' in path:
            return 'password_reset'
        
        # Check for CRUD operations
        if method == 'POST':
            if 'upload' in path or 'import' in path:
                return 'upload'
            elif 'download' in path or 'export' in path:
                return 'download'
            else:
                return 'create'
        elif method == 'PUT' or method == 'PATCH':
            return 'update'
        elif method == 'DELETE':
            return 'delete'
        elif method == 'GET':
            if 'api' in path:
                return 'api_call'
            elif 'download' in path or 'export' in path:
                return 'download'
            else:
                return 'view'
        
        # Check for permission denied
        if status_code == 403:
            return 'permission_denied'
        
        return 'view'
    
    def get_safe_request_data(self, request):
        """Safely extract request data without sensitive information"""
        data = {}
        
        try:
            # GET parameters
            if request.GET:
                data['get_params'] = dict(request.GET)
            
            # POST parameters (excluding sensitive fields)
            if request.POST:
                post_data = {}
                sensitive_fields = ['password', 'token', 'secret', 'key', 'csrf']
                for key, value in request.POST.items():
                    if not any(field in key.lower() for field in sensitive_fields):
                        post_data[key] = value
                if post_data:
                    data['post_params'] = post_data
            
            # Additional request info
            data['content_type'] = request.content_type
            data['content_length'] = request.META.get('CONTENT_LENGTH', 0)
            
        except Exception as e:
            logger.error(f"Error extracting request data: {str(e)}")
            data['error'] = 'Failed to extract request data'
        
        return data
    
    def analyze_security(self, request, response):
        """Analyze request for suspicious activity"""
        is_suspicious = False
        security_flags = []
        risk_level = 'low'
        
        try:
            ips = getattr(request, "_connection_ips", None) or extract_connection_ips(request)
            ip_address = ips["client_ip"]
            user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
            path = request.path.lower()
            query_string = request.META.get('QUERY_STRING', '').lower()
            
            # Check for malicious user agents
            for malicious_agent in self.MALICIOUS_USER_AGENTS:
                if malicious_agent in user_agent:
                    is_suspicious = True
                    security_flags.append(f'Malicious user agent: {malicious_agent}')
                    risk_level = 'high'
            
            # Check for suspicious patterns in URL and parameters
            full_request = f"{path}?{query_string}"
            for pattern in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, full_request, re.IGNORECASE):
                    is_suspicious = True
                    security_flags.append(f'Suspicious pattern detected: {pattern}')
                    risk_level = 'high'
            
            # Check for unusual HTTP methods
            if request.method in ['TRACE', 'OPTIONS', 'CONNECT']:
                is_suspicious = True
                security_flags.append(f'Unusual HTTP method: {request.method}')
                risk_level = 'medium'
            
            # Check for failed authentication attempts (but be more lenient)
            if response.status_code == 401 or (response.status_code == 403 and 'login' in path):
                # Only mark as suspicious if it's not a known company IP or user
                if not self.is_company_ip(ip_address) and not self.is_known_user(request):
                    is_suspicious = True
                    security_flags.append('Failed authentication attempt')
                    risk_level = 'medium'
            
            # Check for rate limiting violations (if implemented)
            if response.status_code == 429:
                is_suspicious = True
                security_flags.append('Rate limit exceeded')
                risk_level = 'high'
            
            # Check for unusual response codes
            if response.status_code >= 500:
                security_flags.append(f'Server error: {response.status_code}')
                risk_level = 'medium'
            
            # Check for very large requests
            content_length_str = request.META.get('CONTENT_LENGTH', '0')
            try:
                content_length = int(content_length_str) if content_length_str else 0
            except (ValueError, TypeError):
                content_length = 0
            if content_length > 10 * 1024 * 1024:  # 10MB
                is_suspicious = True
                security_flags.append('Unusually large request')
                risk_level = 'medium'
            
        except Exception as e:
            logger.error(f"Error in security analysis: {str(e)}")
            security_flags.append('Security analysis failed')
        
        return is_suspicious, security_flags, risk_level
    
    def is_company_ip(self, ip_address):
        """Check if IP is in company range"""
        company_prefixes = ['125.19.224', '152.57.32', '152.57.40', '152.57.37', '223.185.132']
        return any(ip_address.startswith(prefix) for prefix in company_prefixes)
    
    def is_known_user(self, request):
        """Check if request is from a known legitimate user"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Check if it's a known legitimate user
            legitimate_users = ['jagad', 'Mezhi', 'pm']
            return request.user.username in legitimate_users
        return False
    
    def get_location_info(self, ip_address):
        """Get location information for IP address using multiple methods"""
        try:
            # Basic check for local/private IPs
            if ip_address.startswith(('127.', '10.', '192.168.', '172.')) or ip_address == '::1':
                return 'Local Network', 'Local', 'Local'
            
            # Try multiple geolocation methods
            country, city, region = self.get_location_from_api(ip_address)
            
            if not country:
                # Fallback to basic IP analysis
                country, city, region = self.get_basic_location_info(ip_address)
            
            return country or 'Unknown', city or 'Unknown', region or 'Unknown'
            
        except Exception as e:
            logger.error(f"Error getting location info: {str(e)}")
            return 'Error', 'Error', 'Error'
    
    def get_location_from_api(self, ip_address):
        """Get location from free geolocation API"""
        try:
            # Method 1: Try with urllib (built-in Python library)
            country, city, region = self.get_location_with_urllib(ip_address)
            if country:
                return country, city, region
            
            # Method 2: Try with requests if available
            try:
                import requests
                api_url = f"https://ipapi.co/{ip_address}/json/"
                response = requests.get(api_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    country = data.get('country_name', '')
                    city = data.get('city', '')
                    region = data.get('region', '')
                    return country, city, region
            except ImportError:
                logger.info("requests library not available, using urllib fallback")
            except Exception as e:
                logger.warning(f"requests API geolocation failed: {str(e)}")
                
        except Exception as e:
            logger.warning(f"API geolocation failed: {str(e)}")
        
        return '', '', ''
    
    def get_location_with_urllib(self, ip_address):
        """Get location using built-in urllib (no external dependencies)"""
        try:
            import urllib.request
            import json
            
            # Use ip-api.com (free service)
            api_url = f"http://ip-api.com/json/{ip_address}?fields=status,country,city,regionName"
            
            with urllib.request.urlopen(api_url, timeout=5) as response:
                data = json.loads(response.read().decode())
                
                if data.get('status') == 'success':
                    country = data.get('country', '')
                    city = data.get('city', '')
                    region = data.get('regionName', '')
                    return country, city, region
            
        except Exception as e:
            logger.warning(f"urllib geolocation failed: {str(e)}")
        
        return '', '', ''
    
    def get_basic_location_info(self, ip_address):
        """Enhanced location detection based on IP ranges"""
        try:
            # Enhanced country detection based on IP ranges
            
            # India IP ranges
            india_prefixes = [
                '103.', '106.', '117.', '122.', '125.', '150.', '157.', '163.', '164.',
                '165.', '166.', '167.', '168.', '169.', '170.', '171.', '172.', '173.',
                '174.', '175.', '176.', '180.', '182.', '183.', '202.', '203.', '210.',
                '218.', '219.', '220.', '221.', '222.', '223.', '49.', '59.', '61.',
                '110.', '111.', '112.', '113.', '114.', '115.', '116.', '118.', '119.',
                '120.', '121.', '123.', '124.', '126.', '127.', '139.', '144.', '152.'
            ]
            
            # United States IP ranges
            us_prefixes = [
                '8.', '4.', '12.', '15.', '16.', '17.', '18.', '23.', '24.', '50.',
                '63.', '64.', '65.', '66.', '67.', '68.', '69.', '70.', '71.', '72.',
                '73.', '74.', '75.', '76.', '96.', '97.', '98.', '99.', '100.', '104.',
                '107.', '108.', '173.', '174.', '184.', '192.', '198.', '199.', '204.',
                '205.', '206.', '207.', '208.', '209.', '216.'
            ]
            
            # Check IP against ranges
            for prefix in india_prefixes:
                if ip_address.startswith(prefix):
                    return 'India', 'Unknown City', 'Unknown Region'
            
            for prefix in us_prefixes:
                if ip_address.startswith(prefix):
                    return 'United States', 'Unknown City', 'Unknown Region'
            
            # European ranges (basic)
            if ip_address.startswith(('80.', '81.', '82.', '83.', '84.', '85.', '86.', '87.', '88.', '89.')):
                return 'Europe', 'Unknown City', 'Unknown Region'
            
            # China ranges (basic)
            if ip_address.startswith(('1.', '14.', '27.', '36.', '39.', '42.', '58.', '60.', '61.', '101.')):
                return 'China', 'Unknown City', 'Unknown Region'
            
            # Default
            return 'Unknown Country', 'Unknown City', 'Unknown Region'
                
        except Exception as e:
            logger.error(f"Basic location detection failed: {str(e)}")
            return 'Detection Error', 'Detection Error', 'Detection Error'
    
    def create_security_alert(self, request, activity_log, security_flags, risk_level):
        """Create a security alert for suspicious activity"""
        # Skip if models aren't available
        if not SecurityAlert:
            return
            
        try:
            alert_type = 'suspicious_request'
            if 'malicious user agent' in ' '.join(security_flags).lower():
                alert_type = 'malicious_user_agent'
            elif 'sql injection' in ' '.join(security_flags).lower():
                alert_type = 'sql_injection'
            elif 'xss' in ' '.join(security_flags).lower():
                alert_type = 'xss_attempt'
            elif 'failed authentication' in ' '.join(security_flags).lower():
                alert_type = 'brute_force'
            elif 'rate limit' in ' '.join(security_flags).lower():
                alert_type = 'rate_limit_exceeded'
            
            title = f"Suspicious activity detected from {activity_log.ip_address}"
            description = f"Security flags: {', '.join(security_flags)}"
            
            SecurityAlert.objects.create(
                alert_type=alert_type,
                severity=risk_level,
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                ip_address=activity_log.ip_address,
                user_agent=activity_log.user_agent,
                title=title,
                description=description,
                details={
                    'path': request.path,
                    'method': request.method,
                    'security_flags': security_flags,
                    'user_agent': activity_log.user_agent,
                    'timestamp': timezone.now().isoformat(),
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating security alert: {str(e)}")
    
    def trigger_realtime_blocking(self, request, activity_log, security_flags):
        """Trigger real-time blocking for critical threats"""
        try:
            from main.middleware.realtime_ip_blocker import realtime_blocker
            
            ip_address = activity_log.ip_address
            user = getattr(request, 'user', None)
            user_agent = activity_log.user_agent
            country = activity_log.country
            city = activity_log.city
            region = activity_log.region
            
            # Determine activity type and risk level
            activity_type = 'suspicious_activity'
            risk_level = 'critical'
            
            # Check for specific threat patterns
            if any('sql injection' in flag.lower() for flag in security_flags):
                activity_type = 'critical_exploit'
            elif any('xss' in flag.lower() for flag in security_flags):
                activity_type = 'critical_exploit'
            elif any('malicious user agent' in flag.lower() for flag in security_flags):
                activity_type = 'malicious_user_agent'
            elif any('failed authentication' in flag.lower() for flag in security_flags):
                activity_type = 'failed_login'
            elif any('rate limit' in flag.lower() for flag in security_flags):
                activity_type = 'rate_limit_violation'
            
            # Prepare activity details
            activity_details = {
                'security_flags': security_flags,
                'path': request.path,
                'method': request.method,
                'user_agent': user_agent,
                'country': country,
                'city': city,
                'region': region,
            }
            
            # Handle suspicious activity
            realtime_blocker.handle_suspicious_activity(
                ip_address, activity_type, risk_level, 
                details=f"Critical threat detected: {', '.join(security_flags)}", 
                user=user
            )
            
            logger.critical(f"Triggered real-time blocking for IP {ip_address} due to critical threat")
            
        except Exception as e:
            logger.error(f"Error triggering real-time blocking: {str(e)}")


class SessionCleanupMiddleware(MiddlewareMixin):
    """Middleware to clean up inactive sessions"""
    
    def process_request(self, request):
        """Clean up old inactive sessions periodically"""
        # Skip if models aren't available
        if not ActiveUserSession:
            return None
            
        try:
            # Clean up sessions older than 24 hours of inactivity
            cutoff_time = timezone.now() - timezone.timedelta(hours=24)
            ActiveUserSession.objects.filter(
                last_activity__lt=cutoff_time,
                is_active=True
            ).update(is_active=False)
            
        except Exception as e:
            logger.error(f"Error in session cleanup: {str(e)}")
        
        return None
