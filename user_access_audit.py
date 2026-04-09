"""
User Access Audit Script
Comprehensive audit of user permissions, access levels, and capabilities

Usage:
    python user_access_audit.py --username USERNAME --password PASSWORD [--base-url BASE_URL] [--test-pages]

Options:
    --username USERNAME      Username to audit
    --password PASSWORD       Password for the user
    --base-url BASE_URL      Base URL for testing (default: http://localhost:8000)
    --test-pages             Test actual page access by making HTTP requests
    --csv-output FILE        Output CSV file path (default: user_access_report.csv)
"""
import os
import sys
import csv
import argparse
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime

# Import requests at the top level
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Error: 'requests' library is required. Install with: pip install requests")
    sys.exit(1)

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# requests is imported at the top level

# DjangoBrowserSession class (from security_audit.py)
CSRF_COOKIE_NAME = "csrftoken"
CSRF_FORM_FIELD = "csrfmiddlewaretoken"
SESSION_COOKIE_NAME = "sessionid"

class DjangoBrowserSession:
    """Mimics browser behavior for Django apps"""
    def __init__(self, base_url, user_agent=None, verify_tls=True):
        # Ensure base_url doesn't have trailing issues
        base_url = base_url.rstrip("/")
        # If base_url is HTTP, disable SSL verification
        if base_url.startswith('http://'):
            verify_tls = False
        self.base_url = base_url + "/"
        self.s = requests.Session()
        self.s.verify = verify_tls
        # Disable SSL warnings for local development
        if not verify_tls:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.s.headers.update({
            "User-Agent": user_agent or (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.csrf_token = None

    def _abs(self, url):
        return url if url.startswith("http") else urljoin(self.base_url, url.lstrip("/"))

    def _update_tokens_from_response(self, resp):
        if CSRF_COOKIE_NAME in resp.cookies:
            self.csrf_token = resp.cookies.get(CSRF_COOKIE_NAME)
        if not self.csrf_token and resp.headers.get("Content-Type", "").startswith("text/html"):
            import re
            m = re.search(
                rf'name=["\']{CSRF_FORM_FIELD}["\']\s+value=["\']([^"\']+)["\']',
                resp.text, re.IGNORECASE
            )
            if m:
                self.csrf_token = m.group(1)

    def _ensure_csrf(self, url):
        if self.csrf_token:
            return
        resp = self.s.get(self._abs(url), allow_redirects=True)
        self._update_tokens_from_response(resp)

    def _csrf_headers(self, referer_url):
        headers = {}
        if self.csrf_token:
            headers["X-CSRFToken"] = self.csrf_token
        headers["Referer"] = referer_url
        return headers

    def get(self, url, **kwargs):
        try:
            resp = self.s.get(self._abs(url), allow_redirects=True, timeout=10, **kwargs)
            self._update_tokens_from_response(resp)
            return resp
        except requests.exceptions.SSLError as e:
            # If SSL error and we're using HTTP, suggest checking the URL
            if 'http://' in self.base_url:
                raise requests.exceptions.SSLError(
                    f"SSL error connecting to {self.base_url}. "
                    f"Are you sure the URL is correct? "
                    f"If using HTTP (not HTTPS), ensure the URL starts with 'http://'"
                ) from e
            raise
        except requests.exceptions.ConnectionError as e:
            raise requests.exceptions.ConnectionError(
                f"Could not connect to {self.base_url}. "
                f"Please ensure the Django app is running and the URL is correct."
            ) from e

    def post(self, url, data=None, json=None, **kwargs):
        abs_url = self._abs(url)
        self._ensure_csrf(url)
        headers = kwargs.pop("headers", {})
        headers.update(self._csrf_headers(abs_url))
        try:
            resp = self.s.post(abs_url, data=data, json=json, headers=headers,
                              allow_redirects=True, timeout=10, **kwargs)
            self._update_tokens_from_response(resp)
            return resp
        except requests.exceptions.SSLError as e:
            if 'http://' in self.base_url:
                raise requests.exceptions.SSLError(
                    f"SSL error connecting to {self.base_url}. "
                    f"Are you sure the URL is correct?"
                ) from e
            raise
        except requests.exceptions.ConnectionError as e:
            raise requests.exceptions.ConnectionError(
                f"Could not connect to {self.base_url}. "
                f"Please ensure the Django app is running."
            ) from e

    def extract_captcha(self, html_content):
        """Extract captcha key and image URL from login page HTML"""
        import re
        
        # Look for captcha key in hidden input or JavaScript
        captcha_key_match = re.search(
            r'name=["\']captcha_0["\']\s+value=["\']([^"\']+)["\']',
            html_content, re.IGNORECASE
        )
        
        # Look for captcha image URL
        captcha_image_match = re.search(
            r'src=["\']([^"\']*captcha[^"\']*\.(?:png|jpg|jpeg|gif))["\']',
            html_content, re.IGNORECASE
        )
        
        # Also try to find captcha image URL from django-simple-captcha format
        if not captcha_image_match:
            captcha_image_match = re.search(
                r'/captcha/image/([^/]+)/',
                html_content, re.IGNORECASE
            )
            if captcha_image_match:
                captcha_key = captcha_image_match.group(1)
                captcha_image_url = f"{self.base_url.rstrip('/')}/captcha/image/{captcha_key}/"
                return captcha_key, captcha_image_url
        
        captcha_key = captcha_key_match.group(1) if captcha_key_match else None
        
        if captcha_image_match:
            captcha_image_url = captcha_image_match.group(1)
            if not captcha_image_url.startswith('http'):
                captcha_image_url = self._abs(captcha_image_url)
        else:
            captcha_image_url = None
        
        return captcha_key, captcha_image_url

    def login(self, login_path="/accounts/login/", username=None, password=None,
              username_field="username", password_field="password", extra_form=None,
              captcha_value=None, bypass_captcha=False):
        """
        Login with optional captcha handling.
        
        Args:
            captcha_value: Pre-solved captcha value (if available)
            bypass_captcha: If True and Django available, bypass captcha check
        """
        try:
            r1 = self.get(login_path)
        except requests.exceptions.SSLError as e:
            print(f"\n❌ SSL Error: {e}")
            print(f"   Tip: If using HTTP (not HTTPS), ensure your base URL starts with 'http://'")
            print(f"   Current base URL: {self.base_url}")
            raise
        except requests.exceptions.ConnectionError as e:
            print(f"\n❌ Connection Error: {e}")
            print(f"   Please ensure:")
            print(f"   1. Django app is running")
            print(f"   2. Base URL is correct: {self.base_url}")
            print(f"   3. App is accessible at that URL")
            raise
        
        # Check if captcha is required
        html_content = r1.text
        captcha_key, captcha_image_url = self.extract_captcha(html_content)
        
        form = {
            username_field: username,
            password_field: password,
        }
        
        # Handle captcha
        if captcha_key:
            if bypass_captcha and DJANGO_AVAILABLE:
                # Try to get captcha answer from Django database
                try:
                    from captcha.models import CaptchaStore
                    captcha_obj = CaptchaStore.objects.get(hashkey=captcha_key)
                    captcha_value = captcha_obj.response
                    form['captcha_0'] = captcha_key
                    form['captcha_1'] = captcha_value
                except Exception as e:
                    # Fall back to manual entry
                    if not captcha_value:
                        print(f"\n⚠️  CAPTCHA detected but could not auto-solve: {e}")
                        print(f"   Captcha image URL: {captcha_image_url or 'N/A'}")
                        print(f"   Please solve the captcha manually or use --captcha-value option")
                        raise ValueError("CAPTCHA required but not provided. Use --captcha-value or --bypass-captcha")
            elif captcha_value:
                # Use provided captcha value
                form['captcha_0'] = captcha_key
                form['captcha_1'] = captcha_value
            else:
                # No captcha value provided
                print(f"\n⚠️  CAPTCHA detected on login page")
                print(f"   Captcha key: {captcha_key}")
                if captcha_image_url:
                    print(f"   Captcha image URL: {captcha_image_url}")
                    print(f"   Please solve the captcha and use --captcha-value option")
                else:
                    print(f"   Please solve the captcha manually or use --captcha-value option")
                raise ValueError("CAPTCHA required but not provided. Use --captcha-value or --bypass-captcha")
        
        if extra_form:
            form.update(extra_form)
        if self.csrf_token and CSRF_FORM_FIELD not in form:
            form[CSRF_FORM_FIELD] = self.csrf_token
        
        r2 = self.post(login_path, data=form)
        ok = (r2.status_code in (200, 302)) and (SESSION_COOKIE_NAME in self.s.cookies)
        return ok, r2


# Setup Django environment
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')

try:
    import django
    django.setup()
    
    from django.contrib.auth.models import User
    from main.models import UserProfile
    from main.permissions import (
        user_has_feature, user_has_capability, get_all_features, 
        get_all_roles, user_has_app_access, get_role_label
    )
    from api.models import APIUser, APIKey, ActiveToken, TablePermission
    DJANGO_AVAILABLE = True
except Exception as e:
    DJANGO_AVAILABLE = False
    print(f"Warning: Could not setup Django environment: {e}")
    print("   Some features will be limited (page testing only)")


def get_user_profile_info(user):
    """Get user profile information"""
    try:
        profile = user.userprofile
        return {
            'role': profile.role,
            'role_label': get_role_label(profile.role) if DJANGO_AVAILABLE else profile.role,
            'accessible_countries': profile.accessible_countries.split(',') if profile.accessible_countries else [],
            'accessible_portfolios': profile.accessible_portfolios.split(',') if profile.accessible_portfolios else [],
            'accessible_sites': profile.accessible_sites.split(',') if profile.accessible_sites else [],
            'app_access': profile.list_app_access() if hasattr(profile, 'list_app_access') else [],
            'ticketing_access': profile.ticketing_access,
        }
    except UserProfile.DoesNotExist:
        return None
    except Exception as e:
        return {'error': str(e)}


def get_user_features(user):
    """Get all features the user has access to"""
    if not DJANGO_AVAILABLE:
        return {}
    
    features = {}
    all_features = get_all_features()
    
    for feature_key, feature_label in all_features.items():
        if user_has_feature(user, feature_key):
            features[feature_key] = feature_label
    
    return features


def get_user_capabilities(user):
    """Get all capabilities the user has"""
    if not DJANGO_AVAILABLE:
        return {}
    
    # Get all known capabilities from permissions module
    from main.permissions import list_all_capabilities, _fetch_capability_snapshot
    
    capabilities = {}
    try:
        capability_snapshot = _fetch_capability_snapshot()
        for cap_key, cap_label in capability_snapshot.items():
            if user_has_capability(user, cap_key):
                capabilities[cap_key] = cap_label
    except Exception as e:
        print(f"Warning: Could not fetch capabilities: {e}")
    
    return capabilities


def get_api_user_info(user):
    """Get API user information"""
    if not DJANGO_AVAILABLE:
        return None
    
    try:
        api_users = APIUser.objects.filter(user=user)
        if not api_users.exists():
            return None
        
        api_info = []
        for api_user in api_users:
            # Get active API keys
            api_keys = APIKey.objects.filter(api_user=api_user, is_active=True)
            active_keys = []
            for key in api_keys:
                active_keys.append({
                    'key_prefix': key.key_prefix,
                    'created_at': key.created_at.isoformat() if key.created_at else None,
                    'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None,
                })
            
            # Get active tokens
            active_tokens = ActiveToken.objects.filter(api_user=api_user, is_valid=True)
            tokens = []
            for token in active_tokens:
                tokens.append({
                    'token_prefix': token.token[:20] + '...' if len(token.token) > 20 else token.token,
                    'created_at': token.created_at.isoformat() if token.created_at else None,
                    'expires_at': token.expires_at.isoformat() if token.expires_at else None,
                })
            
            # Get table permissions
            table_perms = TablePermission.objects.filter(api_user=api_user)
            tables = []
            for perm in table_perms:
                tables.append({
                    'table_name': perm.table_name,
                    'can_read': perm.can_read,
                    'can_filter': perm.can_filter,
                    'can_aggregate': perm.can_aggregate,
                    'max_records': perm.max_records_per_request,
                })
            
            api_info.append({
                'name': api_user.name,
                'status': api_user.status,
                'access_level': api_user.access_level,
                'is_active': api_user.is_active,
                'rate_limit_per_minute': api_user.rate_limit_per_minute,
                'rate_limit_per_hour': api_user.rate_limit_per_hour,
                'rate_limit_per_day': api_user.rate_limit_per_day,
                'total_requests': api_user.total_requests,
                'last_request_at': api_user.last_request_at.isoformat() if api_user.last_request_at else None,
                'active_api_keys': active_keys,
                'active_tokens': tokens,
                'table_permissions': tables,
            })
        
        return api_info
    except Exception as e:
        return {'error': str(e)}


def test_page_access(session, url_path):
    """Test if user can access a specific page"""
    try:
        resp = session.get(url_path, timeout=5)
        return {
            'url': url_path,
            'status_code': resp.status_code,
            'accessible': resp.status_code == 200,
            'redirected': resp.status_code in (301, 302, 303, 307, 308),
            'final_url': resp.url if resp.url != session._abs(url_path) else None,
        }
    except requests.exceptions.SSLError as e:
        return {
            'url': url_path,
            'status_code': None,
            'accessible': False,
            'error': f'SSL Error: {str(e)}',
        }
    except requests.exceptions.ConnectionError as e:
        return {
            'url': url_path,
            'status_code': None,
            'accessible': False,
            'error': f'Connection Error: {str(e)}',
        }
    except Exception as e:
        return {
            'url': url_path,
            'status_code': None,
            'accessible': False,
            'error': str(e),
        }


def get_test_urls():
    """Get list of URLs to test"""
    return [
        '/',
        '/dashboard/',
        '/accounts/login/',
        '/accounts/logout/',
        '/accounts/profile/',
        '/user-management/',
        '/data-upload/',
        '/analytics/',
        '/portfolio-map/',
        '/yield-report/',
        '/kpi-dashboard/',
        '/sales/',
        '/pr-gap/',
        '/revenue-loss/',
        '/areas-of-concern/',
        '/bess-performance/',
        '/generation-report/',
        '/time-series-dashboard/',
        '/ticketing/',
        '/ticketing/my-tickets/',
        '/ticketing/create/',
        '/ticketing/admin/',
        '/api/dashboard/',
        '/api/manual/',
    ]


def audit_user(username, password, base_url, test_pages=False, captcha_value=None, bypass_captcha=False):
    """Perform comprehensive user access audit"""
    print(f"\n{'='*80}")
    print(f"User Access Audit Report")
    print(f"{'='*80}")
    print(f"Username: {username}")
    print(f"Base URL: {base_url}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    # Validate base URL
    if not base_url.startswith(('http://', 'https://')):
        print("❌ Error: Base URL must start with 'http://' or 'https://'")
        print(f"   Provided: {base_url}")
        print(f"   Example: http://localhost:8000")
        return None
    
    # Initialize browser session
    try:
        session = DjangoBrowserSession(base_url)
    except Exception as e:
        print(f"❌ Error initializing session: {e}")
        return None
    
    # Try to login
    print("🔐 Attempting login...")
    try:
        login_success, login_resp = session.login(
            username=username, 
            password=password,
            captcha_value=captcha_value,
            bypass_captcha=bypass_captcha
        )
    except ValueError as e:
        # CAPTCHA-related error
        print(f"❌ {e}")
        if "CAPTCHA" in str(e):
            print(f"\n💡 To handle CAPTCHA:")
            print(f"   1. Use --bypass-captcha flag (requires Django access)")
            print(f"   2. Use --captcha-value VALUE (provide solved captcha)")
            print(f"   3. Open the captcha image URL in browser and solve manually")
        return None
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL Error during login: {e}")
        print(f"\n💡 Troubleshooting:")
        print(f"   1. If using HTTP (not HTTPS), ensure URL starts with 'http://'")
        print(f"   2. If Django redirects HTTP to HTTPS, use HTTPS URL")
        print(f"   3. For local development, use: http://localhost:8000")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        print(f"\n💡 Troubleshooting:")
        print(f"   1. Ensure Django app is running: python manage.py runserver")
        print(f"   2. Check if the URL is correct: {base_url}")
        print(f"   3. Verify the app is accessible in a browser")
        return None
    except Exception as e:
        print(f"❌ Unexpected error during login: {e}")
        return None
    
    if not login_success:
        print("❌ Login failed!")
        print(f"   Status code: {login_resp.status_code}")
        print(f"   Response URL: {login_resp.url}")
        if login_resp.status_code == 200:
            # Check for error messages in response
            if 'error' in login_resp.text.lower() or 'invalid' in login_resp.text.lower():
                print("   Error: Invalid credentials or account disabled")
        return None
    
    print("✅ Login successful!\n")
    
    # Get Django user object
    user = None
    if DJANGO_AVAILABLE:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            print(f"⚠️  Warning: User '{username}' not found in database")
            user = None
    
    # Collect audit data
    audit_data = {
        'username': username,
        'timestamp': datetime.now().isoformat(),
        'base_url': base_url,
        'login_successful': True,
    }
    
    # Basic user info
    print("📋 User Information:")
    print("-" * 80)
    if user:
        audit_data['user_info'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
        }
        print(f"  User ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Active: {user.is_active}")
        print(f"  Staff: {user.is_staff}")
        print(f"  Superuser: {user.is_superuser}")
        print(f"  Date Joined: {user.date_joined}")
        print(f"  Last Login: {user.last_login}")
    else:
        audit_data['user_info'] = {'error': 'User not found in database'}
        print("  ⚠️  User not found in database (Django not available)")
    print()
    
    # User profile
    print("👤 User Profile:")
    print("-" * 80)
    if user:
        profile_info = get_user_profile_info(user)
        if profile_info:
            audit_data['profile'] = profile_info
            print(f"  Role: {profile_info.get('role_label', profile_info.get('role', 'N/A'))}")
            print(f"  App Access: {', '.join(profile_info.get('app_access', [])) or 'None'}")
            print(f"  Ticketing Access: {profile_info.get('ticketing_access', False)}")
            
            countries = profile_info.get('accessible_countries', [])
            portfolios = profile_info.get('accessible_portfolios', [])
            sites = profile_info.get('accessible_sites', [])
            
            print(f"  Accessible Countries: {len(countries)}")
            if countries:
                print(f"    {', '.join([c.strip() for c in countries if c.strip()])}")
            
            print(f"  Accessible Portfolios: {len(portfolios)}")
            if portfolios:
                print(f"    {', '.join([p.strip() for p in portfolios if p.strip()])}")
            
            print(f"  Accessible Sites: {len(sites)}")
            if sites:
                print(f"    {', '.join([s.strip() for s in sites[:10] if s.strip()])}")
                if len(sites) > 10:
                    print(f"    ... and {len(sites) - 10} more")
        else:
            audit_data['profile'] = {'error': 'No profile found'}
            print("  ⚠️  No user profile found")
    else:
        audit_data['profile'] = {'error': 'User not available'}
        print("  ⚠️  Cannot check profile (Django not available)")
    print()
    
    # Features
    print("🎯 Features Access:")
    print("-" * 80)
    if user:
        features = get_user_features(user)
        audit_data['features'] = features
        print(f"  Total Features: {len(features)}")
        if features:
            for feature_key, feature_label in sorted(features.items()):
                print(f"    ✓ {feature_label} ({feature_key})")
        else:
            print("  ⚠️  No features assigned")
    else:
        audit_data['features'] = {}
        print("  ⚠️  Cannot check features (Django not available)")
    print()
    
    # Capabilities
    print("🔑 Capabilities:")
    print("-" * 80)
    if user:
        capabilities = get_user_capabilities(user)
        audit_data['capabilities'] = capabilities
        print(f"  Total Capabilities: {len(capabilities)}")
        if capabilities:
            # Group by category
            by_category = {}
            for cap_key, cap_label in capabilities.items():
                category = cap_key.split('.')[0] if '.' in cap_key else 'other'
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append((cap_key, cap_label))
            
            for category in sorted(by_category.keys()):
                print(f"  {category.upper()}:")
                for cap_key, cap_label in sorted(by_category[category]):
                    print(f"    ✓ {cap_label} ({cap_key})")
        else:
            print("  ⚠️  No capabilities assigned")
    else:
        audit_data['capabilities'] = {}
        print("  ⚠️  Cannot check capabilities (Django not available)")
    print()
    
    # API User Info
    print("🔌 API User Information:")
    print("-" * 80)
    if user:
        api_info = get_api_user_info(user)
        audit_data['api_users'] = api_info
        if api_info:
            if isinstance(api_info, dict) and 'error' in api_info:
                print(f"  ❌ Error: {api_info['error']}")
            else:
                for idx, api_user in enumerate(api_info, 1):
                    print(f"  API User #{idx}: {api_user['name']}")
                    print(f"    Status: {api_user['status']}")
                    print(f"    Access Level: {api_user['access_level']}")
                    print(f"    Active: {api_user['is_active']}")
                    print(f"    Rate Limits: {api_user['rate_limit_per_minute']}/min, "
                          f"{api_user['rate_limit_per_hour']}/hour, "
                          f"{api_user['rate_limit_per_day']}/day")
                    print(f"    Total Requests: {api_user['total_requests']}")
                    print(f"    Active API Keys: {len(api_user['active_api_keys'])}")
                    if api_user['active_api_keys']:
                        for key in api_user['active_api_keys']:
                            print(f"      - {key['key_prefix']}...")
                    print(f"    Active Tokens: {len(api_user['active_tokens'])}")
                    print(f"    Table Permissions: {len(api_user['table_permissions'])}")
                    if api_user['table_permissions']:
                        for perm in api_user['table_permissions']:
                            print(f"      - {perm['table_name']}: "
                                  f"read={perm['can_read']}, "
                                  f"filter={perm['can_filter']}, "
                                  f"aggregate={perm['can_aggregate']}")
        else:
            print("  ⚠️  Not an API user")
    else:
        audit_data['api_users'] = None
        print("  ⚠️  Cannot check API info (Django not available)")
    print()
    
    # Page Access Testing
    if test_pages:
        print("🌐 Testing Page Access:")
        print("-" * 80)
        test_urls = get_test_urls()
        page_results = []
        
        for url in test_urls:
            print(f"  Testing {url}...", end='\r')
            result = test_page_access(session, url)
            page_results.append(result)
            
            if result.get('accessible'):
                print(f"  ✅ {url} - Accessible (200)")
            elif result.get('redirected'):
                print(f"  ↪️  {url} - Redirected ({result['status_code']}) -> {result.get('final_url', 'unknown')}")
            elif result.get('error'):
                print(f"  ❌ {url} - Error: {result['error']}")
            else:
                print(f"  ❌ {url} - Status: {result.get('status_code', 'unknown')}")
        
        audit_data['page_access'] = page_results
        print()
    
    # Summary
    print("📊 Summary:")
    print("-" * 80)
    if user:
        print(f"  Role: {audit_data.get('profile', {}).get('role_label', 'N/A')}")
        print(f"  Features: {len(audit_data.get('features', {}))}")
        print(f"  Capabilities: {len(audit_data.get('capabilities', {}))}")
        print(f"  App Access: {', '.join(audit_data.get('profile', {}).get('app_access', [])) or 'None'}")
        print(f"  API User: {'Yes' if audit_data.get('api_users') else 'No'}")
        if test_pages:
            accessible = sum(1 for r in audit_data.get('page_access', []) if r.get('accessible'))
            total = len(audit_data.get('page_access', []))
            print(f"  Pages Accessible: {accessible}/{total}")
    print()
    
    return audit_data


def write_csv_report(audit_data, output_file):
    """Write audit data to CSV"""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['User Access Audit Report'])
        writer.writerow(['Username', audit_data['username']])
        writer.writerow(['Timestamp', audit_data['timestamp']])
        writer.writerow(['Base URL', audit_data['base_url']])
        writer.writerow([])
        
        # User Info
        writer.writerow(['USER INFORMATION'])
        if 'user_info' in audit_data and 'error' not in audit_data['user_info']:
            user_info = audit_data['user_info']
            writer.writerow(['Field', 'Value'])
            for key, value in user_info.items():
                writer.writerow([key, value])
        writer.writerow([])
        
        # Profile
        writer.writerow(['USER PROFILE'])
        if 'profile' in audit_data and 'error' not in audit_data['profile']:
            profile = audit_data['profile']
            writer.writerow(['Field', 'Value'])
            writer.writerow(['Role', profile.get('role', 'N/A')])
            writer.writerow(['Role Label', profile.get('role_label', 'N/A')])
            writer.writerow(['App Access', ', '.join(profile.get('app_access', []))])
            writer.writerow(['Ticketing Access', profile.get('ticketing_access', False)])
            writer.writerow(['Accessible Countries', ', '.join(profile.get('accessible_countries', []))])
            writer.writerow(['Accessible Portfolios', ', '.join(profile.get('accessible_portfolios', []))])
            writer.writerow(['Accessible Sites', ', '.join(profile.get('accessible_sites', []))])
        writer.writerow([])
        
        # Features
        writer.writerow(['FEATURES'])
        writer.writerow(['Feature Key', 'Feature Label'])
        if 'features' in audit_data:
            for key, label in sorted(audit_data['features'].items()):
                writer.writerow([key, label])
        writer.writerow([])
        
        # Capabilities
        writer.writerow(['CAPABILITIES'])
        writer.writerow(['Capability Key', 'Capability Label'])
        if 'capabilities' in audit_data:
            for key, label in sorted(audit_data['capabilities'].items()):
                writer.writerow([key, label])
        writer.writerow([])
        
        # API Users
        writer.writerow(['API USERS'])
        if 'api_users' in audit_data and audit_data['api_users']:
            for idx, api_user in enumerate(audit_data['api_users'], 1):
                writer.writerow([f'API User #{idx}', api_user['name']])
                writer.writerow(['Status', api_user['status']])
                writer.writerow(['Access Level', api_user['access_level']])
                writer.writerow(['Active', api_user['is_active']])
                writer.writerow(['Active API Keys', len(api_user['active_api_keys'])])
                writer.writerow(['Active Tokens', len(api_user['active_tokens'])])
                writer.writerow(['Table Permissions', len(api_user['table_permissions'])])
                writer.writerow([])
        else:
            writer.writerow(['Status', 'Not an API user'])
        writer.writerow([])
        
        # Page Access
        if 'page_access' in audit_data:
            writer.writerow(['PAGE ACCESS TEST'])
            writer.writerow(['URL', 'Status Code', 'Accessible', 'Redirected', 'Final URL', 'Error'])
            for result in audit_data['page_access']:
                writer.writerow([
                    result.get('url', ''),
                    result.get('status_code', ''),
                    result.get('accessible', False),
                    result.get('redirected', False),
                    result.get('final_url', ''),
                    result.get('error', ''),
                ])


def main():
    parser = argparse.ArgumentParser(
        description='Comprehensive user access audit tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python user_access_audit.py --username john --password secret123
  python user_access_audit.py --username john --password secret123 --test-pages
  python user_access_audit.py --username john --password secret123 --base-url http://production.example.com
  python user_access_audit.py --username john --password secret123 --csv-output custom_report.csv
        """
    )
    
    parser.add_argument('--username', required=True, help='Username to audit')
    parser.add_argument('--password', required=True, help='Password for the user')
    parser.add_argument('--base-url', default='http://localhost:5555',
                       help='Base URL for testing (default: http://localhost:5555)')
    parser.add_argument('--test-pages', action='store_true',
                       help='Test actual page access by making HTTP requests')
    parser.add_argument('--csv-output', default='user_access_report.csv',
                       help='Output CSV file path (default: user_access_report.csv)')
    parser.add_argument('--captcha-value', default=None,
                       help='CAPTCHA value if login page requires CAPTCHA')
    parser.add_argument('--bypass-captcha', action='store_true',
                       help='Bypass CAPTCHA by reading answer from Django database (requires Django access)')
    
    args = parser.parse_args()
    
    # Perform audit
    audit_data = audit_user(
        username=args.username,
        password=args.password,
        base_url=args.base_url,
        test_pages=args.test_pages,
        captcha_value=args.captcha_value,
        bypass_captcha=args.bypass_captcha
    )
    
    if audit_data:
        # Write CSV report
        print(f"\n💾 Writing CSV report to {args.csv_output}...")
        write_csv_report(audit_data, args.csv_output)
        print(f"✅ Report saved to {args.csv_output}")
    else:
        print("\n❌ Audit failed - no data collected")
        sys.exit(1)


if __name__ == '__main__':
    main()

