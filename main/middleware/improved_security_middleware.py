"""
Improved Security Middleware with Smart IP Blocking
Distinguishes between legitimate users and malicious attackers
"""

import time
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden, HttpResponse
from django.template.loader import render_to_string
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.contrib.auth.models import User

# Import real-time blocker
from .realtime_ip_blocker import realtime_blocker
from shared_app.utils.email_utils import build_email_subject

logger = logging.getLogger(__name__)

class ImprovedSecurityMiddleware(MiddlewareMixin):
    """Enhanced security middleware with smart IP blocking"""
    
    # Known malicious IPs (from your logs)
    KNOWN_MALICIOUS_IPS = {
        '207.180.211.42',  # PEAR injection attacker
        '78.153.140.156',  # Androxgh0st attacker
        '45.67.138.250',   # Laravel exploit attempts
        '185.244.104.2',   # WebDAV scanner
        '199.45.155.65',   # CensysInspect scanner
        '167.94.146.49',   # CensysInspect scanner
        '20.245.134.45',   # mrtscan
        '64.227.191.115',  # Endpoint scanner
    }
    
    # Legitimate company IPs (add your company's IP ranges)
    COMPANY_IP_RANGES = [
        '125.19.224.0/24',   # Your company range
        '152.57.32.0/24',    # Your company range
        '152.57.40.0/24',    # Your company range
        '152.57.37.0/24',    # Your company range
        '223.185.132.0/24',  # Your company range
    ]
    
    # High-risk patterns (these should always be blocked)
    HIGH_RISK_PATTERNS = [
        r'\.\./',           # Directory traversal
        r'<script',         # XSS
        r'javascript:',     # XSS
        r'union.*select',   # SQL injection
        r'drop.*table',     # SQL injection
        r'exec\(',          # Code execution
        r'eval\(',          # Code execution
        r'base64_decode',   # Potential payload
        r'cmd\.exe',        # Command execution
        r'wget|curl',       # Download attempts
        r'pearcmd',         # PEAR command injection
        r'config-create',   # PEAR command injection
        r'phpinfo',         # Information disclosure
        r'\.env',           # Environment file access
    ]
    
    # Malicious user agents
    MALICIOUS_USER_AGENTS = [
        'libredtail-http',
        'sqlmap',
        'nmap',
        'nikto',
        'dirb',
        'gobuster',
        'burpsuite',
        'owasp',
        'zgrab',
        'censysinspect',
        'mrtscan',
        'python-requests',
        'scanner',
    ]
    
    # Suspicious file extensions
    SUSPICIOUS_EXTENSIONS = [
        '.php', '.asp', '.aspx', '.jsp', '.py', '.sh', '.bat', '.cmd',
        '.exe', '.pif', '.scr', '.vbs', '.js', '.jar'
    ]
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        
        # Thresholds for different types of blocking
        self.FAILED_LOGIN_THRESHOLD = 10  # Block after 10 failed logins from same IP
        self.SUSPICIOUS_PATTERN_THRESHOLD = 3  # Block after 3 high-risk patterns
        self.RATE_LIMIT_THRESHOLD = 100  # Requests per minute
        
        # Protected gateway IP that should NEVER be blocked (Docker WSL gateway)
        self.PROTECTED_GATEWAY_IP = '172.25.32.1'
        
    def process_request(self, request):
        """Process incoming request for security checks"""
        # Check for cache reload signal first
        realtime_blocker.check_cache_reload_signal()
        
        # Note: Static and media files are now handled by authenticated views
        # Security checks still apply (IP blocking, pattern detection, etc.)
        # Authentication is handled by serve_static_file and serve_media_file views
        path = request.path.lower()
        
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        path = request.path.lower()
        
        # Check for suspicious host headers (after IP but before bypassing)
        host_header = request.META.get('HTTP_HOST', '').lower()
        # Detect suspicious host patterns (tunneling services, suspicious subdomains)
        suspicious_host_patterns = [
            r'^\d+-\d+-\d+-\d+\.',  # IP-like subdomains (e.g., 47-247-169-94.cprapid.com)
            r'\.ngrok\.io',          # Ngrok tunnels
            r'\.cprapid\.com',       # Crapid hosting (suspicious)
            r'\.localtest\.me',      # Local testing subdomain
            r'localhost-\d+',        # Strange localhost patterns
        ]
        
        for pattern in suspicious_host_patterns:
            if re.search(pattern, host_header):
                logger.critical(f"🚨 SUSPICIOUS HOST HEADER detected: {host_header} from IP: {ip_address}")
                # Store alert info to send with response details later
                request._security_alert = {
                    'ip_address': ip_address,
                    'threat_type': f"Suspicious Host Header: {host_header}",
                    'details': f"Host pattern: {pattern}",
                    'user_agent': user_agent
                }
                # Break after first match found
                break
        
        # ⚡ IMPORTANT: Protected gateway IP - skip blocking but STILL detect and alert
        # This IP is the Docker WSL gateway where all users appear as this IP
        if ip_address == self.PROTECTED_GATEWAY_IP:
            logger.debug(f"Skipping blocking checks for protected gateway IP: {ip_address}")
            
            # STILL monitor for security threats and send alerts even for protected IP
            # This ensures you're notified of suspicious activity from gateway IP
            full_request = f"{path}?{request.META.get('QUERY_STRING', '')}"
            
            # Check for high-risk patterns and alert
            for pattern in self.HIGH_RISK_PATTERNS:
                if re.search(pattern, full_request, re.IGNORECASE):
                    logger.critical(f"🚨 HIGH RISK PATTERN detected from protected IP {ip_address}: {pattern}")
                    # Store alert info to send with response details later
                    request._security_alert = {
                        'ip_address': ip_address,
                        'threat_type': f"High-Risk Pattern: {pattern}",
                        'details': f"Request: {full_request}",
                        'user_agent': user_agent
                    }
                    # Continue - don't block, but alert will be sent
            
            # Check for malicious user agents and alert
            for malicious_agent in self.MALICIOUS_USER_AGENTS:
                if malicious_agent in user_agent:
                    logger.critical(f"🚨 MALICIOUS USER AGENT detected from protected IP {ip_address}: {malicious_agent}")
                    # Store alert info to send with response details later
                    request._security_alert = {
                        'ip_address': ip_address,
                        'threat_type': f"Malicious User Agent: {malicious_agent}",
                        'details': f"User Agent: {user_agent}",
                        'user_agent': user_agent
                    }
                    # Continue - don't block, but alert will be sent
            
            return None  # Allow all traffic from this IP
        
        # Always block known malicious IPs
        if ip_address in self.KNOWN_MALICIOUS_IPS:
            logger.warning(f"Blocked known malicious IP: {ip_address}")
            return self.create_blocking_response(
                "Known Malicious IP",
                "This IP address has been identified as malicious and is permanently blocked.",
                ip_address
            )
        
        # Check if IP is already blocked by real-time blocker
        if realtime_blocker.is_ip_blocked(ip_address):
            logger.warning(f"Blocked by real-time system: {ip_address}")
            return self.create_blocking_response(
                "Suspicious Activity Detected",
                "This IP address has been blocked due to detected suspicious activity patterns.",
                ip_address
            )
        
        # Check if user is blocked (for company IPs)
        if hasattr(request, 'user') and request.user.is_authenticated:
            if realtime_blocker.is_user_blocked(request.user.username):
                logger.warning(f"Blocked user account: {request.user.username}")
                return self.create_blocking_response(
                    "User Account Disabled",
                    "Your user account has been temporarily disabled due to suspicious activity.",
                    ip_address,
                    user=request.user,
                    is_user_blocked=True
                )
        
        # Check if IP is in company range
        is_company_ip = self.is_company_ip(ip_address)
        
        # Block malicious user agents (regardless of IP)
        for malicious_agent in self.MALICIOUS_USER_AGENTS:
            if malicious_agent in user_agent:
                logger.warning(f"Blocked malicious user agent: {user_agent}")
                # Trigger real-time blocking
                realtime_blocker.handle_suspicious_activity(
                    ip_address, 'malicious_user_agent', 'high', 
                    details=f"User agent: {user_agent}", user=getattr(request, 'user', None)
                )
                return self.create_blocking_response(
                    "Malicious User Agent Detected",
                    f"Your browser/application ({user_agent}) has been identified as potentially malicious.",
                    ip_address,
                    user=getattr(request, 'user', None)
                )
        
        # Check for high-risk patterns (always block these)
        full_request = f"{path}?{request.META.get('QUERY_STRING', '')}"
        for pattern in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, full_request, re.IGNORECASE):
                logger.critical(f"Blocked high-risk pattern from {ip_address}: {pattern}")
                # Trigger real-time blocking
                realtime_blocker.handle_suspicious_activity(
                    ip_address, 'high_risk_pattern', 'critical',
                    details=f"Pattern: {pattern}, Request: {full_request}", 
                    user=getattr(request, 'user', None)
                )
                return self.create_blocking_response(
                    "High-Risk Attack Pattern Detected",
                    f"A potentially dangerous request pattern was detected: {pattern}",
                    ip_address,
                    user=getattr(request, 'user', None)
                )
        
        # Check for suspicious file extensions
        if any(path.endswith(ext) for ext in self.SUSPICIOUS_EXTENSIONS):
            logger.warning(f"Blocked suspicious file extension from {ip_address}: {path}")
            return self.create_blocking_response(
                "Suspicious File Access Attempt",
                f"Attempted to access a suspicious file type: {path}",
                ip_address,
                user=getattr(request, 'user', None)
            )
        
        # Rate limiting (more lenient for company IPs)
        rate_limit = self.RATE_LIMIT_THRESHOLD * 2 if is_company_ip else self.RATE_LIMIT_THRESHOLD
        if self.is_rate_limited(ip_address, rate_limit):
            logger.warning(f"Rate limit exceeded for IP: {ip_address}")
            return self.create_blocking_response(
                "Rate Limit Exceeded",
                f"Too many requests from this IP address. Please wait before trying again. (Limit: {rate_limit} requests per minute)",
                ip_address,
                user=getattr(request, 'user', None)
            )
        
        return None
    
    def process_response(self, request, response):
        """Process response and analyze for suspicious activity"""
        ip_address = self.get_client_ip(request)
        path = request.path.lower()
        
        # Send any pending security alerts with response details
        if hasattr(request, '_security_alert'):
            alert_info = request._security_alert
            self._send_protected_ip_security_alert(
                alert_info['ip_address'],
                alert_info['threat_type'],
                details=alert_info['details'],
                user_agent=alert_info['user_agent'],
                response=response,
                path=path
            )
        
        # Check for failed login attempts
        if response.status_code == 403 and 'login' in path:
            # For company IPs, use user-based blocking instead of IP blocking
            if realtime_blocker.is_company_ip(ip_address) and hasattr(request, 'user') and request.user.is_authenticated:
                realtime_blocker.block_user_immediately(
                    request.user.username, 
                    f"Failed login attempt to {path} from company IP"
                )
            else:
                # Trigger real-time blocking analysis for external IPs
                realtime_blocker.handle_suspicious_activity(
                    ip_address, 'failed_login', 'medium',
                    details=f"Failed login attempt to {path}", 
                    user=getattr(request, 'user', None)
                )
        
        # Add security headers with smart frame options
        # Critical security pages - Block all frames (only truly sensitive pages)
        critical_pages = [
            '/admin/', '/accounts/login/', '/accounts/logout/',
            '/accounts/password-reset/'
        ]
        
        # Dashboard pages - Allow same-origin frames for functionality
        dashboard_pages = [
            '/unified-operations-dashboard/', '/portfolio-map/', '/kpi-dashboard/',
            '/sales/', '/generation-report/', '/yield-report/', '/revenue-loss/',
            '/bess-performance/', '/time-series-dashboard/', '/analytics/', '/user-management/',
            '/site-onboarding/', '/data-upload/', '/data-upload-help/', '/security-alerts/'
        ]
        
        # API and download pages - Allow same-origin for dashboard functionality
        functional_pages = [
            '/api/', '/api/analytics/', '/download-user-activity/', '/download/', '/upload/',
            '/static/', '/media/'
        ]
        
        # Smart frame options - context-aware security
        if any(path.startswith(page) for page in critical_pages):
            response['X-Frame-Options'] = 'DENY'  # Maximum security for truly sensitive pages
        elif any(path.startswith(page) for page in dashboard_pages):
            response['X-Frame-Options'] = 'SAMEORIGIN'  # Allow iframes for dashboards
        elif any(path.startswith(page) for page in functional_pages):
            response['X-Frame-Options'] = 'SAMEORIGIN'  # Allow iframes for API/downloads
        else:
            response['X-Frame-Options'] = 'SAMEORIGIN'  # Default to allow iframes for unknown pages
        
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_company_ip(self, ip_address):
        """Check if IP address is in company range"""
        try:
            import ipaddress
            
            for ip_range in self.COMPANY_IP_RANGES:
                if ipaddress.ip_address(ip_address) in ipaddress.ip_network(ip_range):
                    return True
            return False
        except:
            # Fallback: check if IP starts with known company prefixes
            company_prefixes = ['125.19.224', '152.57.32', '152.57.40', '152.57.37', '223.185.132']
            return any(ip_address.startswith(prefix) for prefix in company_prefixes)
    
    def is_rate_limited(self, ip_address, limit):
        """Check if IP is rate limited"""
        cache_key = f"rate_limit_{ip_address}"
        current_time = time.time()
        
        # Get current request count, handle Redis connection errors gracefully
        try:
            request_times = cache.get(cache_key, [])
        except Exception:
            # If cache is unavailable (e.g., Redis connection error), skip rate limiting
            # This allows the application to continue functioning without Redis
            logger.warning(f"Cache unavailable for rate limiting, skipping check for IP: {ip_address}")
            return False
        
        # Remove old requests (older than 1 minute)
        request_times = [t for t in request_times if current_time - t < 60]
        
        # Check if rate limit exceeded
        if len(request_times) >= limit:
            return True
        
        # Add current request
        request_times.append(current_time)
        try:
            cache.set(cache_key, request_times, 60)
        except Exception:
            # If cache set fails, continue without caching
            pass
        
        return False
    
    # REMOVED: should_block_failed_logins() method - cache-based login tracking removed
    # Login attempt tracking is now handled exclusively by the database (LoginAttempt model)
    # This ensures consistency and a single source of truth for rate limiting
    
    def record_suspicious_activity(self, ip_address, pattern, risk_level):
        """Record suspicious activity for analysis"""
        cache_key = f"suspicious_{ip_address}"
        current_time = timezone.now()
        
        # Get current suspicious activities, handle Redis connection errors gracefully
        try:
            activities = cache.get(cache_key, [])
        except Exception:
            # If cache is unavailable, start with empty list
            logger.warning(f"Cache unavailable for suspicious activity tracking, starting fresh for IP: {ip_address}")
            activities = []
        
        # Remove old activities (older than 24 hours)
        one_day_ago = current_time - timedelta(hours=24)
        activities = [activity for activity in activities if activity['time'] > one_day_ago]
        
        # Add current activity
        activities.append({
            'time': current_time,
            'pattern': pattern,
            'risk_level': risk_level
        })
        
        # Store updated activities, handle Redis connection errors gracefully
        try:
            cache.set(cache_key, activities, 86400)  # 24 hours
        except Exception:
            # If cache set fails, continue without caching
            logger.warning(f"Failed to cache suspicious activity for IP: {ip_address}")
            pass
        
        # Auto-block if too many high-risk activities
        high_risk_activities = [a for a in activities if a['risk_level'] == 'critical']
        if len(high_risk_activities) >= self.SUSPICIOUS_PATTERN_THRESHOLD:
            self.KNOWN_MALICIOUS_IPS.add(ip_address)
            logger.critical(f"Auto-blocked IP {ip_address} due to {len(high_risk_activities)} high-risk activities")
    
    def create_blocking_response(self, reason, details, ip_address, user=None, is_user_blocked=False):
        """Create a detailed blocking response with explanation"""
        context = {
            'reason': reason,
            'details': details,
            'ip_address': ip_address,
            'user': user,
            'is_user_blocked': is_user_blocked,
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S IST'),
            'contact_email': 'administrator',  # Generic administrator reference
        }
        
        # Create HTML response
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Access Blocked - Peak Energy</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
                .block-container {{ background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
                .alert-icon {{ font-size: 4rem; color: #dc3545; }}
                .contact-info {{ background: #f8f9fa; border-radius: 10px; padding: 20px; }}
            </style>
        </head>
        <body>
            <div class="container d-flex align-items-center justify-content-center min-vh-100">
                <div class="block-container p-5 text-center" style="max-width: 600px;">
                    <div class="alert-icon mb-4">🚫</div>
                    <h1 class="text-danger mb-4">Access Blocked</h1>
                    
                    <div class="alert alert-danger mb-4">
                        <h4 class="alert-heading">Security Alert</h4>
                        <p class="mb-0"><strong>Reason:</strong> {reason}</p>
                        <hr>
                        <p class="mb-0"><strong>Details:</strong> {details}</p>
                    </div>
                    
                    <div class="contact-info mb-4">
                        <h5>What happened?</h5>
                        <p class="mb-2">
                            {'Your user account has been temporarily disabled due to suspicious activity.' if is_user_blocked else 'Your IP address has been blocked due to detected suspicious activity.'}
                        </p>
                        <p class="mb-0">
                            <strong>Time:</strong> {context['timestamp']}<br>
                            <strong>IP Address:</strong> {ip_address}<br>
                            {'<strong>User:</strong> ' + user.username if user else ''}
                        </p>
                    </div>
                    
                    <div class="alert alert-info">
                        <h6>Need Help?</h6>
                        <p class="mb-0">
                            If you believe this is an error, please contact your system administrator with the details above.
                        </p>
                    </div>
                    
                    <div class="mt-4">
                        <a href="/" class="btn btn-primary">Return to Home</a>
                        <a href="/accounts/login/" class="btn btn-outline-secondary ms-2">Login Page</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        response = HttpResponse(html_content, status=403)
        response['Content-Type'] = 'text/html; charset=utf-8'
        return response

    def _send_protected_ip_security_alert(self, ip_address, threat_type, details=None, user_agent="", response=None, path=""):
        """Send security alert email for threats from protected IP (even though not blocking)"""
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            # Prepare email details
            subject = build_email_subject(
                f"🚨 SECURITY ALERT: Suspicious Activity from Protected IP {ip_address}"
            )
            
            # Handle details formatting outside f-string (can't use backslash in f-string)
            details_line = ''
            if details:
                # Build string with backslashes first, then format
                newline = '\n'
                details_line = f"{newline}Details: {details}{newline}"
            
            # Add server response information if available
            server_response_info = ''
            if response:
                newline = '\n'
                status_code = response.status_code
                response_size = len(response.content) if hasattr(response, 'content') else 0
                
                # Determine if server was compromised
                intrusion_status = '✅ Server responded normally'
                if status_code in [200, 301, 302, 304]:
                    intrusion_status = '✅ Server responded normally'
                elif status_code == 403:
                    intrusion_status = '🛡️ Server denied access (protected)'
                elif status_code == 404:
                    intrusion_status = '✅ Server responded normally (not found)'
                elif status_code == 500:
                    intrusion_status = '⚠️ Server error occurred'
                elif status_code >= 400:
                    intrusion_status = '⚠️ Client error response'
                
                server_response_info = f"""{newline}Server Response:
- HTTP Status: {status_code}
- Response Size: {response_size} bytes
- Path Accessed: {path}
- Intrusion Status: {intrusion_status}{newline}"""
            
            message = f"""
SECURITY ALERT - SUSPICIOUS ACTIVITY DETECTED

⚠️ IMPORTANT: This is a security alert from a PROTECTED IP that would normally be whitelisted.
The system detected suspicious activity but did NOT block the IP to avoid disrupting legitimate users.

Details:
- Protected IP: {ip_address}
- Threat Type: {threat_type}
- Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
- User Agent: {user_agent}
{details_line}{server_response_info}
Action Required:
1. Review the activity logs immediately
2. Investigate if this is legitimate or malicious
3. Check if a real attacker is using the gateway IP
4. Consider manual intervention if needed

Note: The IP was NOT automatically blocked to prevent false positives,
but you should investigate this suspicious activity immediately.

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
            
            logger.info(f"Protected IP security alert email sent for {ip_address} to {recipient_email}")
            
        except Exception as e:
            logger.error(f"Failed to send protected IP security alert email for {ip_address}: {str(e)}")
    
    def get_security_report(self):
        """Get security report for admin dashboard"""
        return {
            'blocked_ips': list(self.KNOWN_MALICIOUS_IPS),
            'company_ip_ranges': self.COMPANY_IP_RANGES,
            'failed_login_threshold': self.FAILED_LOGIN_THRESHOLD,
            'suspicious_pattern_threshold': self.SUSPICIOUS_PATTERN_THRESHOLD,
            'rate_limit_threshold': self.RATE_LIMIT_THRESHOLD,
        }
