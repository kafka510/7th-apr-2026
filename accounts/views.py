from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetView
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect, HttpResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.urls import reverse_lazy, reverse
from django.core.mail import BadHeaderError
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import smtplib
import logging
from captcha.models import CaptchaStore
from captcha.helpers import captcha_image_url
import random
import string

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('main:unified_operations_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def _login_captcha_context():
    """Build context for login template; omit captcha when disabled."""
    if getattr(settings, 'CAPTCHA_DISABLED', False):
        return {'captcha_key': None}
    return {'captcha_key': CaptchaStore.generate_key()}


@ensure_csrf_cookie
def login_view(request):
    if request.method == 'POST':
        # Verify CAPTCHA first (skip when CAPTCHA_DISABLED is True)
        if not getattr(settings, 'CAPTCHA_DISABLED', False):
            captcha_key = request.POST.get('captcha_0', '')
            captcha_value = request.POST.get('captcha_1', '')
            
            if not captcha_key or not captcha_value:
                messages.error(request, 'Please complete the CAPTCHA verification.')
                return render(request, 'accounts/login.html', {
                    'form': AuthenticationForm(),
                    'captcha_failed': True,
                    **_login_captcha_context()
                })
            
            # Verify CAPTCHA
            try:
                captcha_obj = CaptchaStore.objects.get(hashkey=captcha_key)
                if captcha_obj.response.lower() != captcha_value.lower():
                    messages.error(request, 'Invalid CAPTCHA. Please try again.')
                    captcha_obj.delete()  # Delete used CAPTCHA
                    return render(request, 'accounts/login.html', {
                        'form': AuthenticationForm(),
                        'captcha_failed': True,
                        **_login_captcha_context()
                    })
                # Delete used CAPTCHA after successful verification
                captcha_obj.delete()
            except CaptchaStore.DoesNotExist:
                messages.error(request, 'CAPTCHA expired or invalid. Please try again.')
                return render(request, 'accounts/login.html', {
                    'form': AuthenticationForm(),
                    'captcha_failed': True,
                    **_login_captcha_context()
                })
        
        # Check if user is blocked BEFORE form validation
        username = request.POST.get('username', '').strip()
        if username:
            # Import LoginAttempt model
            from .models import LoginAttempt
            
            # Check for rate limiting (3 attempts per minute)
            if LoginAttempt.is_locked_out(username, max_attempts=3, lockout_minutes=1):
                time_remaining = LoginAttempt.get_lockout_time_remaining(username, minutes=1)
                if time_remaining > 0:
                    messages.error(request, f'Too many failed login attempts. Please try again after {time_remaining} seconds.')
                    return render(request, 'accounts/login.html', {
                        'form': AuthenticationForm(),
                        'locked_out': True,
                        'time_remaining': time_remaining,
                        'username': username,
                        **_login_captcha_context()
                    })
            
            try:
                from main.middleware.realtime_ip_blocker import realtime_blocker
                from django.contrib.auth.models import User
                
                # Check if user exists and is blocked
                # Use is_user_blocked() method which checks both database and cache
                try:
                    user_obj = User.objects.get(username=username)
                    # Check database first, then cache (more reliable)
                    is_blocked = (realtime_blocker.is_user_blocked(username) or not user_obj.is_active)
                except User.DoesNotExist:
                    is_blocked = False
                
                if is_blocked:
                    # User is already blocked - don't record failed attempt
                    # Recording failed attempts for already-blocked users was a bug that
                    # created false failed attempt counts. Users who are already blocked
                    # should not have their login attempts counted as failures.
                    ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0')
                    
                    # Log the blocked login attempt for security monitoring
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Blocked user {username} attempted to login from IP {ip_address}. "
                        f"User is already blocked - not recording as failed attempt."
                    )
                    
                    # Create blocking response with enhanced messaging
                    from django.http import HttpResponse
                    from django.utils import timezone
                    from main.middleware.realtime_ip_blocker import realtime_blocker
                    
                    # Get blocking details
                    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
                    current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S IST')
                    
                    # Get failed attempt count (excludes this attempt since user is already blocked)
                    failed_attempts = LoginAttempt.get_recent_failed_attempts(username, minutes=60) if username else 0
                    
                    # Check if IP is blocked
                    is_ip_blocked = realtime_blocker.is_ip_blocked(ip_address) if ip_address != 'Unknown' else False
                    
                    # Create copyable report message
                    report_message = f"""ACCOUNT BLOCKED - SUPPORT REQUEST

Username: {username}
IP Address: {ip_address}
Time: {current_time}
User Agent: {user_agent}
Failed Login Attempts (last hour): {failed_attempts}
IP Blocked: {'Yes' if is_ip_blocked else 'No'}
Account Status: Disabled

Reason: Account has been temporarily disabled due to suspicious activity or multiple failed login attempts.

Please unblock my account and help me regain access. I believe this may be an error or I may have forgotten my password.

Thank you."""
                    
                    html_content = f"""
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Account Disabled - Peak Energy</title>
                        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                        <style>
                            body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
                            .block-container {{ background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 800px; margin: 0 auto; }}
                            .alert-icon {{ font-size: 4rem; color: #dc3545; }}
                            .warning-banner {{ background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; }}
                            .warning-banner h4 {{ margin: 0; font-weight: bold; }}
                            .contact-info {{ background: #f8f9fa; border-radius: 10px; padding: 20px; margin-bottom: 20px; }}
                            .copyable-box {{ background: #fff3cd; border: 2px dashed #ffc107; border-radius: 8px; padding: 15px; margin: 15px 0; position: relative; }}
                            .copyable-box textarea {{ width: 100%; min-height: 150px; border: none; background: transparent; resize: vertical; font-family: monospace; font-size: 12px; }}
                            .copy-btn {{ position: absolute; top: 10px; right: 10px; }}
                            .security-tips {{ background: #e7f3ff; border-left: 4px solid #2196F3; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                            .security-tips ul {{ margin-bottom: 0; padding-left: 20px; }}
                            .info-badge {{ display: inline-block; padding: 5px 10px; background: #17a2b8; color: white; border-radius: 5px; font-size: 12px; margin: 2px; }}
                        </style>
                    </head>
                    <body>
                        <div class="container d-flex align-items-center justify-content-center min-vh-100">
                            <div class="block-container p-5">
                                <!-- Warning Banner -->
                                <div class="warning-banner text-center">
                                    <h4>⚠️ ACCOUNT TEMPORARILY DISABLED</h4>
                                    <p class="mb-0">Your account has been disabled for security reasons</p>
                                </div>
                                
                                <!-- Main Alert -->
                                <div class="alert alert-danger mb-4">
                                    <h4 class="alert-heading">🔒 Security Alert</h4>
                                    <p class="mb-2"><strong>Status:</strong> Account Disabled</p>
                                    <p class="mb-2"><strong>Reason:</strong> Multiple failed login attempts or suspicious activity detected</p>
                                    <p class="mb-0"><strong>Failed Attempts (Last Hour):</strong> {failed_attempts}</p>
                                </div>
                                
                                <!-- Account Details -->
                                <div class="contact-info">
                                    <h5>📋 Account Information</h5>
                                    <p class="mb-2">
                                        <span class="info-badge">Username: {username}</span>
                                        <span class="info-badge">IP: {ip_address}</span>
                                        <span class="info-badge">Time: {current_time}</span>
                                    </p>
                                    <p class="mb-0 text-muted small">
                                        <strong>User Agent:</strong> {user_agent[:100]}{'...' if len(user_agent) > 100 else ''}
                                    </p>
                                </div>
                                
                                <!-- Copyable Report Message -->
                                <div class="copyable-box">
                                    <button class="btn btn-sm btn-warning copy-btn" onclick="copyReportMessage()" title="Copy to clipboard">
                                        📋 Copy Report
                                    </button>
                                    <label class="form-label"><strong>📝 Report Message for Administrator</strong></label>
                                    <p class="text-muted small mb-2">Copy this message and send it to your administrator to request account unblocking:</p>
                                    <textarea id="reportMessage" readonly>{report_message}</textarea>
                                </div>
                                
                                <!-- Security Recommendations -->
                                <div class="security-tips">
                                    <h6><strong>🔐 Security Recommendations</strong></h6>
                                    <ul>
                                        <li><strong>Reset Your Password:</strong> If you've forgotten your password, use the password reset feature once your account is unblocked</li>
                                        <li><strong>Contact Administrator:</strong> Send the report message above to your system administrator</li>
                                        <li><strong>Check Your Credentials:</strong> Ensure you're using the correct username and password</li>
                                        <li><strong>Account Security:</strong> Consider enabling two-factor authentication for better security</li>
                                        <li><strong>Wait Period:</strong> Your account may be automatically unblocked after a security review period</li>
                                    </ul>
                                </div>
                                
                                <!-- Password Reset Link -->
                                <div class="alert alert-warning">
                                    <h6><strong>🔑 Forgot Your Password?</strong></h6>
                                    <p class="mb-2">If you've forgotten your password, you can request a password reset once your account is unblocked.</p>
                                    <a href="/accounts/password_reset/" class="btn btn-sm btn-warning">Request Password Reset</a>
                                </div>
                                
                                <!-- Action Buttons -->
                                <div class="text-center mt-4">
                                    <a href="/accounts/login/" class="btn btn-primary">Return to Login</a>
                                    <a href="/" class="btn btn-outline-secondary ms-2">Return to Home</a>
                                </div>
                            </div>
                        </div>
                        
                        <script>
                            function copyReportMessage() {{
                                const textarea = document.getElementById('reportMessage');
                                textarea.select();
                                textarea.setSelectionRange(0, 99999); // For mobile devices
                                try {{
                                    document.execCommand('copy');
                                    const btn = event.target;
                                    const originalText = btn.innerHTML;
                                    btn.innerHTML = '✓ Copied!';
                                    btn.classList.add('btn-success');
                                    btn.classList.remove('btn-warning');
                                    setTimeout(() => {{
                                        btn.innerHTML = originalText;
                                        btn.classList.remove('btn-success');
                                        btn.classList.add('btn-warning');
                                    }}, 2000);
                                }} catch (err) {{
                                    alert('Failed to copy. Please select and copy manually.');
                                }}
                            }}
                        </script>
                    </body>
                    </html>
                    """
                    
                    response = HttpResponse(html_content, status=403)
                    response['Content-Type'] = 'text/html; charset=utf-8'
                    return response
            except Exception as e:
                # If there's an error checking blocked users, continue with normal login
                pass
        
        # Continue with normal login process
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                # FIX 3: Check if user is blocked AFTER successful authentication but BEFORE login
                # This allows users with correct credentials to be authenticated, but prevents
                # blocked users from actually logging in. This is more secure than checking
                # before authentication (which blocks even with correct credentials).
                try:
                    from main.middleware.realtime_ip_blocker import realtime_blocker
                    is_blocked = (realtime_blocker.is_user_blocked(username) or not user.is_active)
                    
                    if is_blocked:
                        # User authenticated successfully but is blocked - log and show blocking page
                        import logging
                        logger = logging.getLogger(__name__)
                        ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0')
                        logger.warning(
                            f"User {username} authenticated successfully but is blocked. "
                            f"IP: {ip_address}. Preventing login."
                        )
                        
                        # Don't record as failed attempt - user had correct credentials
                        # Just show blocking page
                        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
                        current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S IST')
                        
                        # Get failed attempt count (real failed attempts, not blocked login attempts)
                        from accounts.models import LoginAttempt
                        failed_attempts = LoginAttempt.get_recent_failed_attempts(username, minutes=60) if username else 0
                        
                        # Check if IP is blocked
                        is_ip_blocked = realtime_blocker.is_ip_blocked(ip_address) if ip_address != 'Unknown' else False
                        
                        # Create copyable report message
                        report_message = f"""ACCOUNT BLOCKED - SUPPORT REQUEST

Username: {username}
IP Address: {ip_address}
Time: {current_time}
User Agent: {user_agent}
Failed Login Attempts (last hour): {failed_attempts}
IP Blocked: {'Yes' if is_ip_blocked else 'No'}
Account Status: Disabled

Reason: Account has been temporarily disabled due to suspicious activity or multiple failed login attempts.

Please unblock my account and help me regain access. I believe this may be an error or I may have forgotten my password.

Thank you."""
                        
                        # Reuse the blocking page HTML from above (lines 162-276)
                        from django.http import HttpResponse
                        html_content = f"""
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <title>Account Disabled - Peak Energy</title>
                            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                            <style>
                                body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
                                .block-container {{ background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 800px; margin: 0 auto; }}
                                .alert-icon {{ font-size: 4rem; color: #dc3545; }}
                                .warning-banner {{ background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; }}
                                .warning-banner h4 {{ margin: 0; font-weight: bold; }}
                                .contact-info {{ background: #f8f9fa; border-radius: 10px; padding: 20px; margin-bottom: 20px; }}
                                .copyable-box {{ background: #fff3cd; border: 2px dashed #ffc107; border-radius: 8px; padding: 15px; margin: 15px 0; position: relative; }}
                                .copyable-box textarea {{ width: 100%; min-height: 150px; border: none; background: transparent; resize: vertical; font-family: monospace; font-size: 12px; }}
                                .copy-btn {{ position: absolute; top: 10px; right: 10px; }}
                                .security-tips {{ background: #e7f3ff; border-left: 4px solid #2196F3; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                                .security-tips ul {{ margin-bottom: 0; padding-left: 20px; }}
                                .info-badge {{ display: inline-block; padding: 5px 10px; background: #17a2b8; color: white; border-radius: 5px; font-size: 12px; margin: 2px; }}
                            </style>
                        </head>
                        <body>
                            <div class="container d-flex align-items-center justify-content-center min-vh-100">
                                <div class="block-container p-5">
                                    <div class="warning-banner text-center">
                                        <h4>⚠️ ACCOUNT TEMPORARILY DISABLED</h4>
                                        <p class="mb-0">Your account has been disabled for security reasons</p>
                                    </div>
                                    <div class="alert alert-danger mb-4">
                                        <h4 class="alert-heading">🔒 Security Alert</h4>
                                        <p class="mb-2"><strong>Status:</strong> Account Disabled</p>
                                        <p class="mb-2"><strong>Reason:</strong> Multiple failed login attempts or suspicious activity detected</p>
                                        <p class="mb-0"><strong>Failed Attempts (Last Hour):</strong> {failed_attempts}</p>
                                    </div>
                                    <div class="contact-info">
                                        <h5>📋 Account Information</h5>
                                        <p class="mb-2">
                                            <span class="info-badge">Username: {username}</span>
                                            <span class="info-badge">IP: {ip_address}</span>
                                            <span class="info-badge">Time: {current_time}</span>
                                        </p>
                                        <p class="mb-0 text-muted small">
                                            <strong>User Agent:</strong> {user_agent[:100]}{'...' if len(user_agent) > 100 else ''}
                                        </p>
                                    </div>
                                    <div class="copyable-box">
                                        <button class="btn btn-sm btn-warning copy-btn" onclick="copyReportMessage()" title="Copy to clipboard">
                                            📋 Copy Report
                                        </button>
                                        <label class="form-label"><strong>📝 Report Message for Administrator</strong></label>
                                        <p class="text-muted small mb-2">Copy this message and send it to your administrator to request account unblocking:</p>
                                        <textarea id="reportMessage" readonly>{report_message}</textarea>
                                    </div>
                                    <div class="security-tips">
                                        <h6><strong>🔐 Security Recommendations</strong></h6>
                                        <ul>
                                            <li><strong>Reset Your Password:</strong> If you've forgotten your password, use the password reset feature once your account is unblocked</li>
                                            <li><strong>Contact Administrator:</strong> Send the report message above to your system administrator</li>
                                            <li><strong>Check Your Credentials:</strong> Ensure you're using the correct username and password</li>
                                            <li><strong>Account Security:</strong> Consider enabling two-factor authentication for better security</li>
                                            <li><strong>Wait Period:</strong> Your account may be automatically unblocked after a security review period</li>
                                        </ul>
                                    </div>
                                    <div class="alert alert-warning">
                                        <h6><strong>🔑 Forgot Your Password?</strong></h6>
                                        <p class="mb-2">If you've forgotten your password, you can request a password reset once your account is unblocked.</p>
                                        <a href="/accounts/password_reset/" class="btn btn-sm btn-warning">Request Password Reset</a>
                                    </div>
                                    <div class="text-center mt-4">
                                        <a href="/accounts/login/" class="btn btn-primary">Return to Login</a>
                                        <a href="/" class="btn btn-outline-secondary ms-2">Return to Home</a>
                                    </div>
                                </div>
                            </div>
                            <script>
                                function copyReportMessage() {{
                                    const textarea = document.getElementById('reportMessage');
                                    textarea.select();
                                    textarea.setSelectionRange(0, 99999);
                                    try {{
                                        document.execCommand('copy');
                                        const btn = event.target;
                                        const originalText = btn.innerHTML;
                                        btn.innerHTML = '✓ Copied!';
                                        btn.classList.add('btn-success');
                                        btn.classList.remove('btn-warning');
                                        setTimeout(() => {{
                                            btn.innerHTML = originalText;
                                            btn.classList.remove('btn-success');
                                            btn.classList.add('btn-warning');
                                        }}, 2000);
                                    }} catch (err) {{
                                        alert('Failed to copy. Please select and copy manually.');
                                    }}
                                }}
                            </script>
                        </body>
                        </html>
                        """
                        
                        response = HttpResponse(html_content, status=403)
                        response['Content-Type'] = 'text/html; charset=utf-8'
                        return response
                except Exception as e:
                    # If there's an error checking blocked users, log but allow login
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error checking if user {username} is blocked after authentication: {str(e)}")
                    # Continue with login - better to allow access if check fails
                
                # Import LoginAttempt model
                from .models import LoginAttempt
                
                # Get IP address
                ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0')
                
                # Record successful login
                LoginAttempt.objects.create(
                    username=username,
                    ip_address=ip_address,
                    successful=True
                )
                
                # Clear previous failed attempts
                LoginAttempt.clear_attempts(username)
                
                login(request, user)
                
                # Check if user has API-only access (redirect to manual)
                # Users with 'both' access go to normal dashboard but can access manual anytime
                try:
                    from api.models import APIUser
                    api_user = APIUser.objects.get(user=user)
                    if api_user.access_level == 'api_only':
                        # Redirect API-only users to API documentation page
                        messages.info(request, f'Welcome, {username}! You have API-only access. Below is your API documentation.')
                        return redirect('api:api_manual')
                except APIUser.DoesNotExist:
                    pass  # No APIUser, continue to normal dashboard
                
                messages.success(request, f'Welcome back, {username}!')
                return redirect('main:unified_operations_dashboard')
        else:
            # Login failed - record the attempt
            username = request.POST.get('username', '').strip()
            if username:
                from .models import LoginAttempt
                
                # Get IP address
                ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0')
                
                # Record failed attempt
                LoginAttempt.objects.create(
                    username=username,
                    ip_address=ip_address,
                    successful=False
                )
                
                # Check if user is now locked out (rate limiting - 3 attempts per minute)
                failed_attempts_recent = LoginAttempt.get_recent_failed_attempts(username, minutes=1)
                if failed_attempts_recent >= 3:
                    time_remaining = LoginAttempt.get_lockout_time_remaining(username, minutes=1)
                    messages.error(request, f'Too many failed login attempts. Please try again after {time_remaining} seconds.')
                    return render(request, 'accounts/login.html', {
                        'form': AuthenticationForm(),
                        'locked_out': True,
                        'time_remaining': time_remaining,
                        'username': username,
                        **_login_captcha_context()
                    })
                
                # Check for automatic blocking based on total failed attempts (last hour)
                # This triggers hard blocking (account/IP blocking) not just rate limiting
                failed_attempts_last_hour = LoginAttempt.get_recent_failed_attempts(username, minutes=60)
                
                # Get blocking thresholds from realtime_blocker
                try:
                    from main.middleware.realtime_ip_blocker import realtime_blocker
                    is_company_ip = realtime_blocker.is_company_ip(ip_address)
                    
                    # Threshold: 15 for company IPs, 5 for anonymous IPs
                    blocking_threshold = 15 if is_company_ip else 5
                    
                    if failed_attempts_last_hour >= blocking_threshold:
                        # Trigger automatic blocking
                        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
                        
                        # Block the user account if user exists
                        try:
                            from django.contrib.auth.models import User
                            user_obj = User.objects.get(username=username)
                            
                            # Only block if not already blocked
                            if not realtime_blocker.is_user_blocked(username) and user_obj.is_active:
                                # Block user account
                                realtime_blocker.block_user_immediately(
                                    username=username,
                                    reason=f"Excessive failed login attempts: {failed_attempts_last_hour} (threshold: {blocking_threshold})",
                                    ip_address=ip_address,
                                    user_agent=user_agent,
                                    activity_details={
                                        'failed_attempts': failed_attempts_last_hour,
                                        'threshold': blocking_threshold,
                                        'is_company_ip': is_company_ip,
                                        'blocked_automatically': True,
                                        'source': 'login_view_auto_block'
                                    }
                                )
                                logging.warning(f"Automatically blocked user {username} due to {failed_attempts_last_hour} failed login attempts (threshold: {blocking_threshold})")
                            
                        except User.DoesNotExist:
                            # User doesn't exist - this is suspicious, block IP
                            pass
                        
                        # Also block IP for non-company IPs (regardless of whether user exists)
                        if not is_company_ip and not realtime_blocker.is_ip_blocked(ip_address):
                            # Count failed attempts from this IP (all users)
                            from accounts.models import LoginAttempt
                            ip_failed_attempts = LoginAttempt.objects.filter(
                                ip_address=ip_address,
                                successful=False,
                                attempt_time__gte=timezone.now() - timedelta(hours=1)
                            ).count()
                            
                            if ip_failed_attempts >= blocking_threshold:
                                # Block IP directly
                                realtime_blocker.block_ip_immediately(
                                    ip_address=ip_address,
                                    reason=f"Excessive failed login attempts from IP: {ip_failed_attempts} (threshold: {blocking_threshold})",
                                    is_company_ip=False,
                                    user_agent=user_agent,
                                    activity_details={
                                        'failed_attempts': ip_failed_attempts,
                                        'threshold': blocking_threshold,
                                        'blocked_automatically': True,
                                        'source': 'login_view_auto_block',
                                        'usernames_attempted': [username]
                                    }
                                )
                                logging.warning(f"Automatically blocked IP {ip_address} due to {ip_failed_attempts} failed login attempts (threshold: {blocking_threshold})")
                            
                except Exception as e:
                    # If blocking fails, log but continue with normal error message
                    logging.error(f"Error triggering automatic blocking: {str(e)}")
                
                # Show remaining attempts message
                remaining_attempts = 3 - failed_attempts_recent
                messages.error(request, f'Invalid username or password. {remaining_attempts} attempt(s) remaining.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {
        'form': form,
        **_login_captcha_context()
    })

@never_cache
@csrf_protect
@require_http_methods(["POST", "GET"])
def logout_view(request):
    if request.method == "POST" or request.GET.get('confirmed'):
        logout(request)
        response = HttpResponseRedirect('/accounts/login/')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        messages.info(request, 'You have been logged out.')
        return response
    return render(request, 'accounts/logout_confirm.html')

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')


class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view that only shows success when email is actually sent"""
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')
    
    def form_valid(self, form):
        """Override form_valid to check if email was actually sent and if user is blocked"""
        email = form.cleaned_data['email']
        
        # Check if the email exists in our system
        try:
            user = User.objects.get(email=email)
            email_exists = True
            
            # Check if user is blocked
            try:
                from main.middleware.realtime_ip_blocker import realtime_blocker
                is_blocked = (user.username in realtime_blocker.blocked_users or not user.is_active)
            except Exception:
                is_blocked = False
            
            if is_blocked:
                # Create enhanced blocking response for password reset
                from accounts.models import LoginAttempt
                ip_address = self.request.META.get('REMOTE_ADDR', 'Unknown')
                user_agent = self.request.META.get('HTTP_USER_AGENT', 'Unknown')
                current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S IST')
                
                # Get failed attempt count for the user
                try:
                    failed_attempts = LoginAttempt.get_recent_failed_attempts(user.username, minutes=60)
                except:
                    failed_attempts = 0
                
                # Create copyable report message
                report_message = f"""ACCOUNT DISABLED - PASSWORD RESET REQUEST DENIED

Email: {email}
Username: {user.username if user else 'Unknown'}
IP Address: {ip_address}
Time: {current_time}
User Agent: {user_agent[:100]}
Failed Login Attempts (last hour): {failed_attempts}

Reason: Account has been disabled due to suspicious activity or multiple failed login attempts.

Password reset is not available for disabled accounts. Please contact your administrator to unblock your account first.

Thank you."""
                
                html_content = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Account Disabled - Peak Energy</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                    <style>
                        body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
                        .block-container {{ background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 800px; margin: 0 auto; }}
                        .alert-icon {{ font-size: 4rem; color: #dc3545; }}
                        .warning-banner {{ background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; }}
                        .warning-banner h4 {{ margin: 0; font-weight: bold; }}
                        .contact-info {{ background: #f8f9fa; border-radius: 10px; padding: 20px; margin-bottom: 20px; }}
                        .copyable-box {{ background: #fff3cd; border: 2px dashed #ffc107; border-radius: 8px; padding: 15px; margin: 15px 0; position: relative; }}
                        .copyable-box textarea {{ width: 100%; min-height: 150px; border: none; background: transparent; resize: vertical; font-family: monospace; font-size: 12px; }}
                        .copy-btn {{ position: absolute; top: 10px; right: 10px; }}
                        .security-tips {{ background: #e7f3ff; border-left: 4px solid #2196F3; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                        .security-tips ul {{ margin-bottom: 0; padding-left: 20px; }}
                        .info-badge {{ display: inline-block; padding: 5px 10px; background: #17a2b8; color: white; border-radius: 5px; font-size: 12px; margin: 2px; }}
                    </style>
                </head>
                <body>
                    <div class="container d-flex align-items-center justify-content-center min-vh-100">
                        <div class="block-container p-5">
                            <!-- Warning Banner -->
                            <div class="warning-banner text-center">
                                <h4>⚠️ ACCOUNT DISABLED - PASSWORD RESET UNAVAILABLE</h4>
                                <p class="mb-0">Your account must be unblocked before password reset</p>
                            </div>
                            
                            <!-- Main Alert -->
                            <div class="alert alert-danger mb-4">
                                <h4 class="alert-heading">🔒 Security Alert</h4>
                                <p class="mb-2"><strong>Status:</strong> Account Disabled</p>
                                <p class="mb-2"><strong>Reason:</strong> Multiple failed login attempts or suspicious activity detected</p>
                                <p class="mb-0"><strong>Failed Attempts (Last Hour):</strong> {failed_attempts}</p>
                            </div>
                            
                            <!-- Account Details -->
                            <div class="contact-info">
                                <h5>📋 Account Information</h5>
                                <p class="mb-2">
                                    <span class="info-badge">Email: {email}</span>
                                    <span class="info-badge">Username: {user.username if user else 'Unknown'}</span>
                                    <span class="info-badge">IP: {ip_address}</span>
                                    <span class="info-badge">Time: {current_time}</span>
                                </p>
                            </div>
                            
                            <!-- Copyable Report Message -->
                            <div class="copyable-box">
                                <button class="btn btn-sm btn-warning copy-btn" onclick="copyReportMessage()" title="Copy to clipboard">
                                    📋 Copy Report
                                </button>
                                <label class="form-label"><strong>📝 Report Message for Administrator</strong></label>
                                <p class="text-muted small mb-2">Copy this message and send it to your administrator to request account unblocking:</p>
                                <textarea id="reportMessage" readonly>{report_message}</textarea>
                            </div>
                            
                            <!-- Security Recommendations -->
                            <div class="security-tips">
                                <h6><strong>🔐 Next Steps</strong></h6>
                                <ul>
                                    <li><strong>Contact Administrator:</strong> Send the report message above to your system administrator</li>
                                    <li><strong>Account Unblocking Required:</strong> Your account must be unblocked before you can reset your password</li>
                                    <li><strong>After Unblocking:</strong> Once unblocked, you can use the password reset feature</li>
                                    <li><strong>Security Review:</strong> Your administrator will review your account and unblock it if appropriate</li>
                                </ul>
                            </div>
                            
                            <!-- Action Buttons -->
                            <div class="text-center mt-4">
                                <a href="/accounts/login/" class="btn btn-primary">Return to Login</a>
                                <a href="/" class="btn btn-outline-secondary ms-2">Return to Home</a>
                            </div>
                        </div>
                    </div>
                    
                    <script>
                        function copyReportMessage() {{
                            const textarea = document.getElementById('reportMessage');
                            textarea.select();
                            textarea.setSelectionRange(0, 99999);
                            try {{
                                document.execCommand('copy');
                                const btn = event.target;
                                const originalText = btn.innerHTML;
                                btn.innerHTML = '✓ Copied!';
                                btn.classList.add('btn-success');
                                btn.classList.remove('btn-warning');
                                setTimeout(() => {{
                                    btn.innerHTML = originalText;
                                    btn.classList.remove('btn-success');
                                    btn.classList.add('btn-warning');
                                }}, 2000);
                            }} catch (err) {{
                                alert('Failed to copy. Please select and copy manually.');
                            }}
                        }}
                    </script>
                </body>
                </html>
                """
                
                from django.http import HttpResponse
                response = HttpResponse(html_content, status=403)
                response['Content-Type'] = 'text/html; charset=utf-8'
                return response
                
        except User.DoesNotExist:
            email_exists = False
        
        if email_exists:
            try:
                # Generate password reset token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Build reset URL
                reset_url = self.request.build_absolute_uri(
                    reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                )
                
                # Get logo URL
                logo_url = self.request.build_absolute_uri('/static/PEAK_LOGO.jpg')
                
                # Prepare email context
                context = {
                    'user': user,
                    'uid': uid,
                    'token': token,
                    'protocol': self.request.scheme,
                    'domain': self.request.get_host(),
                    'logo_url': logo_url,
                }
                
                # Render HTML email template
                html_message = render_to_string(self.email_template_name, context)
                
                # Render plain text version
                text_message = f"""Hello,

You're receiving this email because you requested a password reset for your account at Peak Energy.

Please go to the following page and choose a new password:
{reset_url}

Your username, in case you've forgotten: {user.get_username}

This link will expire after use or in 24 hours for security reasons.

If you did not request a password reset, please ignore this email or contact support if you have concerns.

Thanks for using our site!
Peak Energy Team
"""
                
                # Get subject
                subject = render_to_string(self.subject_template_name, context).strip()
                
                # Create email message with HTML and plain text alternatives
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email]
                )
                msg.attach_alternative(html_message, "text/html")
                
                # Send email
                logger = logging.getLogger(__name__)
                logger.info(f"Attempting to send password reset email to {user.email}")
                logger.info(f"Email backend: {settings.EMAIL_BACKEND}")
                logger.info(f"Email host: {settings.EMAIL_HOST}")
                logger.info(f"From email: {settings.DEFAULT_FROM_EMAIL}")
                
                try:
                    msg.send()
                    logger.info(f"Password reset email sent successfully to {user.email}")
                    
                    # If we get here, email was sent successfully
                    messages.success(
                        self.request, 
                        f'Password reset email has been sent to {email}. Please check your inbox.'
                    )
                    return redirect(self.success_url)
                except Exception as send_error:
                    logger.error(f"Failed to send password reset email to {user.email}: {str(send_error)}")
                    logger.error(f"Error type: {type(send_error).__name__}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    raise send_error
                    
            except (BadHeaderError, smtplib.SMTPException, Exception) as e:
                # Email sending failed
                logger = logging.getLogger(__name__)
                logger.error(f"Password reset email failed for {email}: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                messages.error(
                    self.request,
                    f'Sorry, there was an error sending the password reset email: {str(e)}. Please check your email configuration or contact support.'
                )
                return render(self.request, self.template_name, {'form': form})
        else:
            # Email doesn't exist, but for security reasons, don't reveal this
            # Still show success message to prevent email enumeration attacks
            messages.info(
                self.request,
                f'If an account with email {email} exists, a password reset email has been sent.'
            )
            return redirect(self.success_url)
