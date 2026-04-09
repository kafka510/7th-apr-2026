"""
Complete Security Audit Script
Combines analysis, CSV generation, and formatted reporting in one script

Usage:
    python security_audit.py [--base-url BASE_URL] [--verify-urls] [--csv-only] [--skip-curl] [--login USERNAME PASSWORD]

Options:
    --base-url BASE_URL    Base URL for verification (default: http://localhost:8000)
    --verify-urls          Enable URL verification (uses browser-like session)
    --csv-only             Only generate CSV, don't show formatted output
    --skip-curl            Skip URL verification even if enabled
    --login USERNAME PASSWORD  Login credentials for authenticated testing
"""
import os
import re
import ast
import csv
import subprocess
import sys
import argparse
from pathlib import Path
from urllib.parse import urljoin

# Fix Windows console encoding for emoji characters
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Try to import requests for browser-like session
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    try:
        print("Warning: 'requests' library not found. Install with: pip install requests")
        print("   URL verification will use curl instead (less accurate for Django apps)")
    except UnicodeEncodeError:
        print("Warning: 'requests' library not found. Install with: pip install requests")
        print("   URL verification will use curl instead")

# Define the base directory
BASE_DIR = Path(__file__).parent

# Configuration
BASE_URL = os.getenv('SECURITY_AUDIT_BASE_URL', 'http://localhost:8000')
VERIFY_URLS = False
SKIP_CURL = False
CSV_ONLY = False

def discover_urls_files():
    """Auto-discover urls.py files in Django apps"""
    urls_files = []
    
    # Always include root urls.py
    root_urls = BASE_DIR / 'web_app' / 'urls.py'
    if root_urls.exists():
        urls_files.append(str(root_urls.relative_to(BASE_DIR)))
    
    # Find all urls.py files in project apps (excluding venv and migrations)
    for urls_file in BASE_DIR.rglob('urls.py'):
        # Skip venv, migrations, and Django internal files
        path_str = str(urls_file)
        if any(x in path_str for x in ['venv', '__pycache__', 'migrations', 'site-packages', '.git']):
            continue
        
        rel_path = str(urls_file.relative_to(BASE_DIR))
        if rel_path not in urls_files:
            urls_files.append(rel_path)
    
    return urls_files

def discover_views_directories():
    """Auto-discover views files and directories in Django apps"""
    views_dirs = []
    seen_paths = set()
    
    # Find all views.py files and views/ directories
    for views_path in BASE_DIR.rglob('views.py'):
        # Skip venv, migrations, and Django internal files
        path_str = str(views_path)
        if any(x in path_str for x in ['venv', '__pycache__', 'migrations', 'site-packages', '.git']):
            continue
        
        rel_path = str(views_path.relative_to(BASE_DIR))
        if rel_path not in seen_paths:
            views_dirs.append(rel_path)
            seen_paths.add(rel_path)
    
    # Find views/ directories
    for views_dir in BASE_DIR.rglob('views'):
        if not views_dir.is_dir():
            continue
        
        # Skip venv, migrations, and Django internal files
        path_str = str(views_dir)
        if any(x in path_str for x in ['venv', '__pycache__', 'migrations', 'site-packages', '.git']):
            continue
        
        rel_path = str(views_dir.relative_to(BASE_DIR))
        if rel_path not in seen_paths:
            views_dirs.append(rel_path)
            seen_paths.add(rel_path)
    
    return views_dirs

# Auto-discover URLs and views (with fallback to manual list)
try:
    URLS_FILES = discover_urls_files()
    VIEWS_DIRS = discover_views_directories()
    AUTO_DISCOVERY_ENABLED = True
except Exception as e:
    # Fallback to manual list if auto-discovery fails
    print(f"⚠️  Auto-discovery failed: {e}. Using manual list.")
    URLS_FILES = [
        'main/urls.py',
        'api/urls.py',
        'accounts/urls.py',
        'ticketing/urls.py',
        'web_app/urls.py'
    ]
    VIEWS_DIRS = [
        'main/views',
        'api/views.py',
        'api/admin_views.py',
        'accounts/views.py',
        'accounts/access_views.py',
        'ticketing/views'
    ]
    AUTO_DISCOVERY_ENABLED = False

# Security mixins to detect
SECURITY_MIXINS = {
    'LoginRequiredMixin': 'LOGIN_REQUIRED',
    'UserPassesTestMixin': 'ROLE_BASED',
    'PermissionRequiredMixin': 'ROLE_BASED',
    'AccessControlMixin': 'ROLE_BASED',
}

# Security decorators
SECURITY_DECORATORS = {
    'login_required': 'LOGIN_REQUIRED',
    'role_required': 'ROLE_BASED',
    'feature_required': 'ROLE_BASED',
    'user_passes_test': 'ROLE_BASED',
    'superuser_required': 'ROLE_BASED',
    'require_api_auth': 'API_AUTH',
    'api_view': 'API_AUTH',
}

results = []

def extract_decorators(node):
    """Extract decorators from a function/class node"""
    decorators = []
    for decorator in node.decorator_list:
        decorator_name = None
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                decorator_name = decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                decorator_name = decorator.func.attr
        elif isinstance(decorator, ast.Name):
            decorator_name = decorator.id
        elif isinstance(decorator, ast.Attribute):
            decorator_name = decorator.attr
        
        if decorator_name:
            decorators.append(decorator_name)
    return decorators

def get_base_classes(class_node):
    """Extract base classes from a class definition"""
    bases = []
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            parts = []
            node = base
            while isinstance(node, ast.Attribute):
                parts.insert(0, node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.insert(0, node.id)
            bases.append('.'.join(parts))
    return bases

def analyze_class_for_security(class_node, class_name, file_path):
    """Analyze a class for security mixins and decorators"""
    security_info = {
        'has_login_mixin': False,
        'has_role_mixin': False,
        'has_api_auth': False,
        'decorators': [],
        'mixins': [],
        'method_decorators': {}
    }
    
    # Check base classes for mixins
    bases = get_base_classes(class_node)
    for base in bases:
        base_name = base.split('.')[-1]
        if base_name in SECURITY_MIXINS:
            security_info['mixins'].append(base_name)
            if SECURITY_MIXINS[base_name] == 'LOGIN_REQUIRED':
                security_info['has_login_mixin'] = True
            elif SECURITY_MIXINS[base_name] == 'ROLE_BASED':
                security_info['has_role_mixin'] = True
            elif SECURITY_MIXINS[base_name] == 'API_AUTH':
                security_info['has_api_auth'] = True
        
        if 'AccessControl' in base_name or 'Permission' in base_name:
            security_info['has_role_mixin'] = True
            security_info['mixins'].append(base_name)
    
    # Check class decorators - look for @method_decorator(login_required, name='dispatch')
    for decorator in class_node.decorator_list:
        if isinstance(decorator, ast.Call):
            # Check if it's method_decorator
            if isinstance(decorator.func, ast.Name) and decorator.func.id == 'method_decorator':
                # Get the first argument (the decorator being applied)
                if decorator.args:
                    first_arg = decorator.args[0]
                    if isinstance(first_arg, ast.Name):
                        decorator_name = first_arg.id
                        if decorator_name in SECURITY_DECORATORS:
                            security_info['method_decorators']['dispatch'] = decorator_name
                            if SECURITY_DECORATORS[decorator_name] == 'LOGIN_REQUIRED':
                                security_info['has_login_mixin'] = True
                            elif SECURITY_DECORATORS[decorator_name] == 'ROLE_BASED':
                                security_info['has_role_mixin'] = True
            elif isinstance(decorator.func, ast.Attribute) and decorator.func.attr == 'method_decorator':
                # Handle django.utils.decorators.method_decorator
                if decorator.args:
                    first_arg = decorator.args[0]
                    if isinstance(first_arg, ast.Name):
                        decorator_name = first_arg.id
                        if decorator_name in SECURITY_DECORATORS:
                            security_info['method_decorators']['dispatch'] = decorator_name
                            if SECURITY_DECORATORS[decorator_name] == 'LOGIN_REQUIRED':
                                security_info['has_login_mixin'] = True
                            elif SECURITY_DECORATORS[decorator_name] == 'ROLE_BASED':
                                security_info['has_role_mixin'] = True
    
    # Also extract regular decorators
    class_decorators = extract_decorators(class_node)
    security_info['decorators'].extend(class_decorators)
    
    # Check for @method_decorator on methods (for method-specific decorators)
    for node in ast.walk(class_node):
        if isinstance(node, ast.FunctionDef):
            method_decorators = extract_decorators(node)
            for dec in method_decorators:
                if 'method_decorator' in dec.lower():
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Name) and 'method_decorator' in decorator.func.id.lower():
                                for arg in decorator.args:
                                    if isinstance(arg, ast.Name):
                                        if arg.id in SECURITY_DECORATORS:
                                            security_info['method_decorators'][node.name] = arg.id
                                            if SECURITY_DECORATORS[arg.id] == 'LOGIN_REQUIRED':
                                                security_info['has_login_mixin'] = True
                                            elif SECURITY_DECORATORS[arg.id] == 'ROLE_BASED':
                                                security_info['has_role_mixin'] = True
    
    return security_info

def analyze_view_file(file_path):
    """Analyze a Python view file for function and class definitions"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=file_path)
        view_info = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                decorators = extract_decorators(node)
                view_info[node.name] = {
                    'type': 'function',
                    'decorators': decorators,
                    'line': node.lineno,
                    'has_login': any('login_required' in str(d).lower() for d in decorators),
                    'has_role': any('role_required' in str(d).lower() or 'feature_required' in str(d).lower() for d in decorators),
                    'has_api_auth': any('api_auth' in str(d).lower() or 'require_api_auth' in str(d).lower() for d in decorators),
                }
            elif isinstance(node, ast.ClassDef):
                security_info = analyze_class_for_security(node, node.name, file_path)
                view_info[node.name] = {
                    'type': 'class',
                    'decorators': security_info['decorators'],
                    'mixins': security_info['mixins'],
                    'method_decorators': security_info['method_decorators'],
                    'line': node.lineno,
                    'has_login': security_info['has_login_mixin'],
                    'has_role': security_info['has_role_mixin'],
                    'has_api_auth': security_info['has_api_auth'],
                }
        
        return view_info
    except Exception as e:
        print(f"⚠️  Error analyzing {file_path}: {e}")
        return {}

def parse_urls_file(urls_file):
    """Parse a urls.py file to extract URL patterns"""
    urls = []
    try:
        with open(urls_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        active_content = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                active_content.append(line)
        content = '\n'.join(active_content)
        
        pattern = r"path\(['\"]([^'\"]+)['\"],\s*(?:views\.|admin_views\.)?(\w+)(?:\.as_view\(\))?(?:,\s*name=['\"]([^'\"]+)['\"])?\)"
        
        matches = re.finditer(pattern, content)
        for match in matches:
            url_path = match.group(1)
            view_name = match.group(2)
            name = match.group(3) if match.group(3) else ''
            
            if not url_path.startswith('#'):
                urls.append({
                    'url': url_path,
                    'view': view_name,
                    'name': name,
                    'file': urls_file
                })
        
        include_pattern = r"path\(['\"]([^'\"]+)['\"],\s*include\([^\)]+\)"
        include_matches = re.finditer(include_pattern, content)
        for match in include_matches:
            url_path = match.group(1)
            if not url_path.startswith('#'):
                urls.append({
                    'url': url_path,
                    'view': 'INCLUDED_MODULE',
                    'name': '',
                    'file': urls_file
                })
    
    except Exception as e:
        print(f"⚠️  Error parsing {urls_file}: {e}")
    
    return urls

def find_view_security(view_name, views_dict):
    """Find security information for a specific view"""
    if view_name in views_dict:
        view_info = views_dict[view_name]
        decorators = view_info.get('decorators', [])
        mixins = view_info.get('mixins', [])
        method_decorators = view_info.get('method_decorators', {})
        
        all_decorators = list(decorators)
        if mixins:
            all_decorators.extend([f"Mixin:{m}" for m in mixins])
        if method_decorators:
            for method, dec in method_decorators.items():
                all_decorators.append(f"MethodDecorator:{dec}")
        
        return {
            'decorators': all_decorators,
            'has_login': view_info.get('has_login', False),
            'has_role': view_info.get('has_role', False),
            'has_api_auth': view_info.get('has_api_auth', False),
            'type': view_info.get('type', 'unknown'),
            'mixins': mixins,
            'method_decorators': method_decorators
        }
    return {
        'decorators': [],
        'has_login': False,
        'has_role': False,
        'has_api_auth': False,
        'type': 'unknown',
        'mixins': [],
        'method_decorators': {}
    }

def check_security_status(security_info):
    """Determine security status based on security information"""
    has_login = security_info.get('has_login', False)
    has_role = security_info.get('has_role', False)
    has_api_auth = security_info.get('has_api_auth', False)
    decorators = security_info.get('decorators', [])
    
    decorator_str = ' '.join(str(d) for d in decorators).lower()
    has_login = has_login or 'login_required' in decorator_str
    has_role = has_role or 'role_required' in decorator_str or 'feature_required' in decorator_str or 'user_passes_test' in decorator_str
    has_api_auth = has_api_auth or 'api_auth' in decorator_str or 'require_api_auth' in decorator_str
    
    if has_login or has_role or has_api_auth:
        if has_role:
            return 'ROLE_BASED', 'Protected with role/feature permissions'
        elif has_api_auth:
            return 'API_AUTH', 'Protected with API authentication'
        else:
            return 'LOGIN_REQUIRED', 'Protected with login'
    else:
        return 'PUBLIC', '⚠️ VULNERABLE: No authentication required'

# Django Browser Session Class
CSRF_COOKIE_NAME = "csrftoken"
CSRF_FORM_FIELD = "csrfmiddlewaretoken"
SESSION_COOKIE_NAME = "sessionid"

class DjangoBrowserSession:
    """Browser-like session for Django apps - handles CSRF tokens and cookies"""
    def __init__(self, base_url, user_agent=None, verify_tls=True):
        self.base_url = base_url.rstrip("/") + "/"
        self.s = requests.Session()
        self.s.verify = verify_tls
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
            m = re.search(
                rf'name=["\']{CSRF_FORM_FIELD}["\']\s+value=["\']([^"\']+)["\']',
                resp.text, re.IGNORECASE
            )
            if m:
                self.csrf_token = m.group(1)

    def _ensure_csrf(self, url):
        if self.csrf_token:
            return
        resp = self.s.get(self._abs(url), allow_redirects=True, timeout=5)
        self._update_tokens_from_response(resp)

    def _csrf_headers(self, referer_url):
        headers = {}
        if self.csrf_token:
            headers["X-CSRFToken"] = self.csrf_token
        headers["Referer"] = referer_url
        return headers

    def get(self, url, **kwargs):
        resp = self.s.get(self._abs(url), allow_redirects=True, timeout=5, **kwargs)
        self._update_tokens_from_response(resp)
        return resp

    def login(self, login_path="/accounts/login/", username=None, password=None,
              username_field="username", password_field="password", extra_form=None):
        r1 = self.get(login_path)
        form = {username_field: username, password_field: password}
        if extra_form:
            form.update(extra_form)
        if self.csrf_token and CSRF_FORM_FIELD not in form:
            form[CSRF_FORM_FIELD] = self.csrf_token
        r2 = self.post(login_path, data=form)
        ok = (r2.status_code in (200, 302)) and (SESSION_COOKIE_NAME in self.s.cookies)
        return ok, r2

    def post(self, url, data=None, json=None, **kwargs):
        abs_url = self._abs(url)
        self._ensure_csrf(url)
        headers = kwargs.pop("headers", {})
        headers.update(self._csrf_headers(abs_url))
        resp = self.s.post(abs_url, data=data, json=json, headers=headers,
                          allow_redirects=True, timeout=5, **kwargs)
        self._update_tokens_from_response(resp)
        return resp

# Global browser session
_browser_session = None

def verify_url_with_browser(url_path, base_url, authenticated=False):
    """Verify URL accessibility using browser-like session"""
    global _browser_session
    
    if SKIP_CURL or not REQUESTS_AVAILABLE:
        return verify_url_with_curl(url_path, base_url)
    
    try:
        if _browser_session is None:
            _browser_session = DjangoBrowserSession(base_url)
        
        full_url = urljoin(base_url.rstrip('/') + '/', url_path.lstrip('/'))
        
        resp = _browser_session.get(url_path)
        status_code = resp.status_code
        final_url = resp.url
        
        # Check if redirected to login
        if 'login' in final_url.lower() or 'accounts/login' in final_url.lower():
            return 'PROTECTED', f'Redirects to login (HTTP {status_code})'
        elif status_code == 200:
            # Check if we got a login page (even if status is 200)
            if 'login' in resp.text.lower() and 'username' in resp.text.lower():
                return 'PROTECTED', f'Shows login page (HTTP {status_code})'
            return 'ACCESSIBLE', f'Returns HTTP {status_code}'
        elif status_code == 403:
            return 'PROTECTED', f'Returns HTTP {status_code} (Forbidden)'
        elif status_code == 404:
            return 'NOT_FOUND', f'Returns HTTP {status_code}'
        elif status_code == 302 or status_code == 301:
            return 'PROTECTED', f'Redirects (HTTP {status_code})'
        else:
            return 'UNKNOWN', f'Returns HTTP {status_code}'
    
    except requests.exceptions.Timeout:
        return 'TIMEOUT', 'Request timed out'
    except requests.exceptions.ConnectionError:
        return 'ERROR', f'Cannot connect to {base_url} - Is the app running?'
    except Exception as e:
        return 'ERROR', str(e)[:100]

def verify_url_with_curl(url_path, base_url):
    """Fallback: Verify URL accessibility using curl"""
    if SKIP_CURL:
        return None, None
    
    try:
        full_url = urljoin(base_url.rstrip('/') + '/', url_path.lstrip('/'))
        
        import platform
        if platform.system() == 'Windows':
            null_device = 'nul'
        else:
            null_device = '/dev/null'
        
        curl_cmd = [
            'curl', '-s', '-o', null_device, '-w', '%{http_code}|%{redirect_url}',
            '-L',
            '--max-time', '3',
            '--connect-timeout', '2',
            '--max-redirs', '5',
            full_url
        ]
        
        result = subprocess.run(
            curl_cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, 
            timeout=5
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if '|' in output:
                status_code, redirect_url = output.split('|', 1)
                status_code = int(status_code) if status_code.isdigit() else 0
                
                if redirect_url and ('login' in redirect_url.lower() or 'accounts/login' in redirect_url):
                    return 'PROTECTED', f'Redirects to login (HTTP {status_code})'
                elif status_code == 200:
                    return 'ACCESSIBLE', f'Returns HTTP {status_code}'
                elif status_code == 403:
                    return 'PROTECTED', f'Returns HTTP {status_code} (Forbidden)'
                elif status_code == 404:
                    return 'NOT_FOUND', f'Returns HTTP {status_code}'
                else:
                    return 'UNKNOWN', f'Returns HTTP {status_code}'
            else:
                return 'ERROR', f'Invalid curl output: {output[:50]}'
        else:
            stderr_msg = result.stderr.strip() if result.stderr else 'No error message'
            if 'Connection refused' in stderr_msg or 'Failed to connect' in stderr_msg:
                return 'ERROR', f'Cannot connect to {base_url} - Is the app running?'
            elif 'timeout' in stderr_msg.lower():
                return 'TIMEOUT', 'Request timed out'
            else:
                return 'ERROR', f'Curl failed: {stderr_msg[:100]}'
    
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', 'Request timed out'
    except FileNotFoundError:
        return 'SKIPPED', 'curl not found (install curl to enable verification)'
    except Exception as e:
        return 'ERROR', str(e)[:100]

def categorize_endpoint(url_info):
    """Categorize an endpoint based on its URL and view"""
    url = url_info.get('URL Path', '').lower()
    view = url_info.get('View Function', '').lower()
    security_status = url_info.get('Security Status', '')
    
    if any(x in url for x in ['login', 'logout', 'register', 'password-reset', 'password_reset']):
        return 'auth', 'Authentication Endpoints (Intentional Public - OK)'
    
    if 'captcha' in url:
        return 'captcha', 'CAPTCHA Endpoints (Intentional Public - OK)'
    
    if any(x in url for x in ['csrf', 'test', 'debug', 'simple-csrf']):
        return 'test', 'Test/Debug Endpoints (Should Remove in Production)'
    
    if 'api/v1/auth/token' in url:
        return 'api_auth', 'API Authentication Endpoints (Check API Key Protection)'
    elif 'api/' in url:
        return 'api', 'API Endpoints (Check API Key Protection)'
    
    if url_info.get('View Function') == 'INCLUDED_MODULE':
        return 'module', 'Included Modules (Check Individual Routes)'
    
    if security_status == 'PUBLIC':
        return 'vulnerable', '⚠️ Potentially Vulnerable Endpoints'
    
    return 'other', 'Other Endpoints'

def display_results(results):
    """Display formatted results"""
    vulnerable = [r for r in results if r.get('Security Status', '') == 'PUBLIC']
    
    print(f'\n{"="*80}')
    print(f'⚠️  SECURITY AUDIT - VULNERABLE URLS CHECK')
    print(f'{"="*80}')
    print(f'Base URL: {BASE_URL}')
    print(f'URL Verification: {"Enabled" if VERIFY_URLS and not SKIP_CURL else "Disabled"}')
    print(f'Total URLs Analyzed: {len(results)}')
    print(f'Vulnerable URLs (PUBLIC): {len(vulnerable)}')
    print(f'{"="*80}\n')
    
    if vulnerable:
        categories = {
            'auth': [],
            'captcha': [],
            'test': [],
            'api': [],
            'api_auth': [],
            'module': [],
            'vulnerable': [],
            'other': []
        }
        
        for r in vulnerable:
            category, _ = categorize_endpoint(r)
            categories[category].append(r)
        
        category_order = [
            ('auth', '📋 Authentication Endpoints (Intentional Public - OK)'),
            ('captcha', '📋 CAPTCHA Endpoints (Intentional Public - OK)'),
            ('api_auth', '📋 API Authentication Endpoints (Check API Key Protection)'),
            ('test', '⚠️  Test/Debug Endpoints (Should Remove in Production)'),
            ('api', '📋 API Endpoints (Check API Key Protection)'),
            ('module', '📋 Included Modules (Check Individual Routes)'),
            ('vulnerable', '🚨 Potentially Vulnerable Endpoints (Review Carefully)'),
            ('other', '📋 Other Public Endpoints')
        ]
        
        for category_key, category_title in category_order:
            if categories[category_key]:
                print(f"{category_title}:")
                for i, r in enumerate(categories[category_key], 1):
                    url = r.get('URL Path', 'N/A')
                    view = r.get('View Function', 'N/A')
                    view_type = r.get('View Type', 'unknown')
                    file_loc = r.get('File Location', 'Unknown')
                    
                    curl_status = r.get('Curl Status', '')
                    curl_details = r.get('Curl Details', '')
                    
                    print(f"  {i}. {url}")
                    print(f"      View: {view} ({view_type})")
                    if file_loc != 'Unknown':
                        print(f"      File: {file_loc}")
                    
                    if VERIFY_URLS and curl_status:
                        status_icon = '✅' if curl_status == 'PROTECTED' else '⚠️' if curl_status == 'ACCESSIBLE' else '❓'
                        print(f"      {status_icon} Curl: {curl_status} - {curl_details}")
                    
                    decorators = r.get('Decorators', 'None')
                    if decorators != 'None':
                        print(f"      Decorators: {decorators}")
                    
                    print()
        
        print(f'\n{"="*80}')
        print("📊 Summary Statistics:")
        print(f"   Total Public Endpoints: {len(vulnerable)}")
        print(f"   Authentication Endpoints: {len(categories['auth'])}")
        print(f"   Test/Debug Endpoints: {len(categories['test'])}")
        print(f"   API Endpoints: {len(categories['api']) + len(categories['api_auth'])}")
        print(f"   Actually Vulnerable: {len(categories['vulnerable'])}")
        print(f"   Included Modules: {len(categories['module'])}")
        print(f'{"="*80}\n')
        
        if categories['vulnerable']:
            print("⚠️  RECOMMENDATIONS:")
            print("   1. Review the 'Potentially Vulnerable Endpoints' listed above")
            print("   2. Add authentication decorators (@login_required, @role_required, etc.)")
            print("   3. For class-based views, use LoginRequiredMixin or AccessControlMixin")
            print("   4. Remove or secure test/debug endpoints in production")
            print()
    else:
        print("✅ No vulnerable URLs found! All endpoints are protected.")
        print()

def main():
    global BASE_URL, VERIFY_URLS, SKIP_CURL, CSV_ONLY
    
    parser = argparse.ArgumentParser(
        description='Complete Security Audit - Analyzes URLs, generates CSV, and displays results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic audit (fast, no curl)
  python security_audit.py

  # With URL verification (requires app running)
  python security_audit.py --verify-urls

  # Production audit
  python security_audit.py --base-url https://your-production.com --verify-urls

  # Generate CSV only
  python security_audit.py --csv-only
        """
    )
    
    parser.add_argument('--base-url', default=BASE_URL, help=f'Base URL for verification (default: {BASE_URL})')
    parser.add_argument('--verify-urls', action='store_true', help='Enable URL verification (uses browser-like session if requests available)')
    parser.add_argument('--csv-only', action='store_true', help='Only generate CSV, don\'t show formatted output')
    parser.add_argument('--skip-curl', action='store_true', help='Skip URL verification even if enabled')
    parser.add_argument('--login', nargs=2, metavar=('USERNAME', 'PASSWORD'), help='Login credentials for authenticated testing')
    
    args = parser.parse_args()
    
    BASE_URL = args.base_url
    VERIFY_URLS = args.verify_urls
    SKIP_CURL = args.skip_curl
    CSV_ONLY = args.csv_only
    LOGIN_CREDENTIALS = args.login if args.login else None
    
    print(f"\n{'='*80}")
    print(f"🔒 Complete Security Audit")
    print(f"{'='*80}")
    print(f"Base URL: {BASE_URL}")
    print(f"URL Verification: {'Enabled' if VERIFY_URLS and not SKIP_CURL else 'Disabled'}")
    if REQUESTS_AVAILABLE:
        print(f"Browser Session: Available (requests library)")
    else:
        print(f"Browser Session: Not available (using curl)")
    if LOGIN_CREDENTIALS:
        print(f"Authentication: Enabled (username: {LOGIN_CREDENTIALS[0]})")
    if AUTO_DISCOVERY_ENABLED:
        print(f"Auto-Discovery: ✅ Enabled (found {len(URLS_FILES)} URL files, {len(VIEWS_DIRS)} view locations)")
    else:
        print(f"Auto-Discovery: ⚠️  Disabled (using manual list)")
    print(f"{'='*80}\n")
    
    # Initialize browser session and login if credentials provided
    if VERIFY_URLS and not SKIP_CURL and REQUESTS_AVAILABLE and LOGIN_CREDENTIALS:
        global _browser_session
        _browser_session = DjangoBrowserSession(BASE_URL)
        print(f"🔐 Attempting to login...")
        success, resp = _browser_session.login(
            login_path="/accounts/login/",
            username=LOGIN_CREDENTIALS[0],
            password=LOGIN_CREDENTIALS[1]
        )
        if success:
            print(f"✅ Login successful - testing endpoints with authentication")
        else:
            print(f"⚠️  Login failed - testing endpoints without authentication")
            print(f"   Status: {resp.status_code}")
            LOGIN_CREDENTIALS = None
        print()
    
    # Analyze all views
    all_views = {}
    
    for views_path in VIEWS_DIRS:
        file_path = BASE_DIR / views_path
        if file_path.exists():
            if file_path.is_file():
                views = analyze_view_file(file_path)
                for view_name, info in views.items():
                    all_views[view_name] = {
                        **info,
                        'file': str(file_path.relative_to(BASE_DIR))
                    }
            elif file_path.is_dir():
                for py_file in file_path.rglob('*.py'):
                    if py_file.name != '__init__.py':
                        views = analyze_view_file(py_file)
                        for view_name, info in views.items():
                            all_views[view_name] = {
                                **info,
                                'file': str(py_file.relative_to(BASE_DIR))
                            }
    
    print(f"✅ Analyzed {len(all_views)} views")
    
    # Parse all URLs
    all_urls = []
    for urls_file in URLS_FILES:
        file_path = BASE_DIR / urls_file
        if file_path.exists():
            urls = parse_urls_file(file_path)
            all_urls.extend(urls)
            print(f"✅ Parsed {len(urls)} URLs from {urls_file}")
    
    print(f"\n{'='*80}")
    print(f"Analyzing security status...")
    if VERIFY_URLS and not SKIP_CURL:
        print(f"⚠️  URL verification enabled - this may take longer")
        print(f"   Use --skip-curl to skip verification if it's hanging")
        
        # Test connection to base URL first
        print(f"\n🔍 Testing connection to {BASE_URL}...")
        if REQUESTS_AVAILABLE:
            test_status, test_details = verify_url_with_browser('', BASE_URL)
        else:
            test_status, test_details = verify_url_with_curl('', BASE_URL)
        
        if test_status == 'ERROR' and 'Cannot connect' in test_details:
            print(f"❌ {test_details}")
            print(f"   The app doesn't appear to be running on {BASE_URL}")
            print(f"   Start your Django app with: python manage.py runserver")
            print(f"   Or skip URL verification with: --skip-curl")
            print(f"\n   Continuing without URL verification...")
            SKIP_CURL = True
        elif test_status in ['ACCESSIBLE', 'PROTECTED', 'NOT_FOUND']:
            method = "browser session" if REQUESTS_AVAILABLE else "curl"
            print(f"✅ Connection successful - {method} verification will proceed")
        else:
            print(f"⚠️  Connection test: {test_status} - {test_details}")
    print(f"{'='*80}\n")
    
    # Create results
    total_urls = len(all_urls)
    processed = 0
    for url_info in all_urls:
        processed += 1
        if processed % 10 == 0 or processed == 1:
            print(f"  Processing {processed}/{total_urls} URLs...", end='\r')
        
        view_name = url_info['view']
        security_info = find_view_security(view_name, all_views)
        
        decorator_list = security_info.get('decorators', [])
        decorator_str = ', '.join(str(d) for d in decorator_list) if decorator_list else 'None'
        
        security_status, security_details = check_security_status(security_info)
        
        role_requirements = []
        mixins = security_info.get('mixins', [])
        if mixins:
            role_requirements.append(f"Mixin-based ({', '.join(mixins)})")
        
        decorator_str_lower = decorator_str.lower()
        if 'role_required' in decorator_str_lower:
            role_requirements.append('Role-based (check code)')
        if 'feature_required' in decorator_str_lower:
            role_requirements.append('Feature-based (check code)')
        if 'user_passes_test' in decorator_str_lower:
            role_requirements.append('Admin role required (user_passes_test)')
        
        role_str = ' | '.join(role_requirements) if role_requirements else 'Any authenticated user' if security_status != 'PUBLIC' else 'None'
        
        # URL verification (browser-like or curl)
        curl_status = None
        curl_details = None
        if VERIFY_URLS and not SKIP_CURL and url_info['view'] != 'INCLUDED_MODULE':
            try:
                if processed % 5 == 0:
                    method = "browser session" if REQUESTS_AVAILABLE else "curl"
                    auth_status = " (authenticated)" if LOGIN_CREDENTIALS else ""
                    print(f"  Processing {processed}/{total_urls} URLs (verifying with {method}{auth_status})...", end='\r')
                
                # Use browser session if available, otherwise fallback to curl
                if REQUESTS_AVAILABLE:
                    curl_status, curl_details = verify_url_with_browser(
                        url_info['url'], 
                        BASE_URL, 
                        authenticated=bool(LOGIN_CREDENTIALS)
                    )
                else:
                    curl_status, curl_details = verify_url_with_curl(url_info['url'], BASE_URL)
                
                # Show first few connection errors to help debug
                if curl_status == 'ERROR' and 'Cannot connect' in curl_details and processed <= 3:
                    print(f"\n⚠️  Warning: {curl_details}")
                    print(f"   URL: {url_info['url']}")
                    print(f"   Full URL would be: {urljoin(BASE_URL.rstrip('/') + '/', url_info['url'].lstrip('/'))}")
                    print(f"   Make sure your Django app is running on {BASE_URL}")
            except KeyboardInterrupt:
                print(f"\n\n⚠️  Interrupted by user. Skipping remaining URL verifications...")
                SKIP_CURL = True
                curl_status = 'SKIPPED'
                curl_details = 'Interrupted'
            except Exception as e:
                curl_status = 'ERROR'
                curl_details = f'Exception: {str(e)[:50]}'
        
        result = {
            'URL Path': url_info['url'],
            'View Function': view_name,
            'URL Name': url_info['name'],
            'Security Status': security_status,
            'Security Details': security_details,
            'Decorators': decorator_str,
            'Role/Feature Requirements': role_str,
            'File Location': all_views.get(view_name, {}).get('file', 'Unknown'),
            'Line Number': all_views.get(view_name, {}).get('line', 'N/A'),
            'View Type': security_info.get('type', 'unknown')
        }
        
        if curl_status:
            result['Curl Status'] = curl_status
            result['Curl Details'] = curl_details
        
        results.append(result)
    
    print(f"\n✅ Processed {processed}/{total_urls} URLs")
    
    # Sort by security status
    results.sort(key=lambda x: (
        x['Security Status'] == 'PUBLIC',
        x.get('Curl Status', '') == 'ACCESSIBLE' if VERIFY_URLS else False,
        x['URL Path']
    ))
    
    # Write to CSV
    csv_file = BASE_DIR / 'security_audit_report.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if results:
            fieldnames = list(results[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    
    print(f"\n✅ Security audit complete!")
    print(f"📊 Total URLs analyzed: {len(results)}")
    vulnerable_count = len([r for r in results if r['Security Status'] == 'PUBLIC'])
    print(f"⚠️  Vulnerable URLs (public): {vulnerable_count}")
    print(f"📝 Report saved to: {csv_file}")
    
    # Display formatted results unless CSV only
    if not CSV_ONLY:
        display_results(results)
    else:
        print(f"\n💡 Run without --csv-only to see formatted analysis")
    
    print(f"\n💡 Tip: Run with --verify-urls --base-url YOUR_URL to verify URLs on production")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()

