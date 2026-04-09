"""
Enhanced Security Audit Analyzer
Analyzes all URLs and views to check for security decorators and permissions
Now includes class-based view detection, mixin inheritance, and curl-based verification

Usage:
    python security_audit_analyzer.py [--base-url BASE_URL] [--verify-urls]

Options:
    --base-url BASE_URL    Base URL for curl verification (default: http://localhost:8000)
    --verify-urls          Enable curl-based URL verification
    --skip-curl            Skip curl verification even if enabled

Output:
    - security_audit_report.csv: Complete list of all URLs with security status
"""
import os
import re
import ast
import csv
import subprocess
import sys
import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Define the base directory
BASE_DIR = Path(__file__).parent

# Configuration
BASE_URL = os.getenv('SECURITY_AUDIT_BASE_URL', 'http://localhost:5555')
VERIFY_URLS = False
SKIP_CURL = False

# URLs to analyze
URLS_FILES = [
    'main/urls.py',
    'api/urls.py',
    'accounts/urls.py',
    'ticketing/urls.py',
    'web_app/urls.py'
]

# Views directories to analyze
VIEWS_DIRS = [
    'main/views',
    'api/views.py',
    'api/admin_views.py',
    'accounts/views.py',
    'accounts/access_views.py',
    'ticketing/views'
]

results = []

# Security mixins to detect
SECURITY_MIXINS = {
    'LoginRequiredMixin': 'LOGIN_REQUIRED',
    'UserPassesTestMixin': 'ROLE_BASED',
    'PermissionRequiredMixin': 'ROLE_BASED',
    'AccessControlMixin': 'ROLE_BASED',  # Custom mixin
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
            # Handle cases like django.contrib.auth.mixins.LoginRequiredMixin
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
        # Check if it's a security mixin
        base_name = base.split('.')[-1]  # Get just the class name
        if base_name in SECURITY_MIXINS:
            security_info['mixins'].append(base_name)
            if SECURITY_MIXINS[base_name] == 'LOGIN_REQUIRED':
                security_info['has_login_mixin'] = True
            elif SECURITY_MIXINS[base_name] == 'ROLE_BASED':
                security_info['has_role_mixin'] = True
            elif SECURITY_MIXINS[base_name] == 'API_AUTH':
                security_info['has_api_auth'] = True
        
        # Check for custom mixins that inherit from security mixins
        if 'AccessControl' in base_name or 'Permission' in base_name:
            security_info['has_role_mixin'] = True
            security_info['mixins'].append(base_name)
    
    # Check class decorators
    class_decorators = extract_decorators(class_node)
    security_info['decorators'].extend(class_decorators)
    
    # Check for @method_decorator on methods
    for node in ast.walk(class_node):
        if isinstance(node, ast.FunctionDef):
            method_decorators = extract_decorators(node)
            for dec in method_decorators:
                if 'method_decorator' in dec.lower():
                    # Try to find the decorator being applied
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Name) and 'method_decorator' in decorator.func.id.lower():
                                # Check arguments
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
            # Analyze function-based views
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
            
            # Analyze class-based views
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
        
        # Skip commented lines
        lines = content.split('\n')
        active_content = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                active_content.append(line)
        content = '\n'.join(active_content)
        
        # Extract path() calls - improved pattern
        # Pattern: path('url/', views.function_name, name='url_name')
        # Also handles: path('url/', views.ClassName.as_view(), name='url_name')
        pattern = r"path\(['\"]([^'\"]+)['\"],\s*(?:views\.|admin_views\.)?(\w+)(?:\.as_view\(\))?(?:,\s*name=['\"]([^'\"]+)['\"])?\)"
        
        matches = re.finditer(pattern, content)
        for match in matches:
            url_path = match.group(1)
            view_name = match.group(2)
            name = match.group(3) if match.group(3) else ''
            
            # Skip if URL is commented out (basic check)
            if not url_path.startswith('#'):
                urls.append({
                    'url': url_path,
                    'view': view_name,
                    'name': name,
                    'file': urls_file
                })
        
        # Also check for include() patterns
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
        
        # Combine all security indicators
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
    
    # Check decorators for security
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

def verify_url_with_curl(url_path, base_url=BASE_URL):
    """Verify URL accessibility using curl"""
    if SKIP_CURL:
        return None, None
    
    try:
        full_url = urljoin(base_url.rstrip('/') + '/', url_path.lstrip('/'))
        
        # Use curl to check if URL redirects to login (indicates protection)
        # Follow redirects and check final status
        curl_cmd = [
            'curl', '-s', '-o', '/dev/null', '-w', '%{http_code}|%{redirect_url}',
            '-L',  # Follow redirects
            '--max-time', '5',  # 5 second timeout
            full_url
        ]
        
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if '|' in output:
                status_code, redirect_url = output.split('|', 1)
                status_code = int(status_code) if status_code.isdigit() else 0
                
                # Check if redirects to login (indicates protection)
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
                return 'ERROR', 'Invalid curl output'
        else:
            return 'ERROR', f'Curl failed: {result.stderr[:100]}'
    
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', 'Request timed out'
    except FileNotFoundError:
        return 'SKIPPED', 'curl not found (install curl to enable verification)'
    except Exception as e:
        return 'ERROR', str(e)[:100]

# Parse command line arguments
parser = argparse.ArgumentParser(description='Security Audit Analyzer')
parser.add_argument('--base-url', default=BASE_URL, help=f'Base URL for verification (default: {BASE_URL})')
parser.add_argument('--verify-urls', action='store_true', help='Enable curl-based URL verification')
parser.add_argument('--skip-curl', action='store_true', help='Skip curl verification')
args = parser.parse_args()

BASE_URL = args.base_url
VERIFY_URLS = args.verify_urls
SKIP_CURL = args.skip_curl

print(f"\n{'='*80}")
print(f"🔒 Enhanced Security Audit Analyzer")
print(f"{'='*80}")
print(f"Base URL: {BASE_URL}")
print(f"URL Verification: {'Enabled' if VERIFY_URLS and not SKIP_CURL else 'Disabled'}")
print(f"{'='*80}\n")

# Analyze all views
all_views = {}

# Analyze views directories
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
print(f"{'='*80}\n")

# Create results
for url_info in all_urls:
    view_name = url_info['view']
    security_info = find_view_security(view_name, all_views)
    
    # Get decorator names as string
    decorator_list = security_info.get('decorators', [])
    decorator_str = ', '.join(str(d) for d in decorator_list) if decorator_list else 'None'
    
    security_status, security_details = check_security_status(security_info)
    
    # Extract role requirements
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
    
    # Curl verification
    curl_status = None
    curl_details = None
    if VERIFY_URLS and not SKIP_CURL and url_info['view'] != 'INCLUDED_MODULE':
        curl_status, curl_details = verify_url_with_curl(url_info['url'], BASE_URL)
    
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

# Sort by security status (vulnerable first)
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

if vulnerable_count > 0:
    print(f"\n⚠️  First few potentially vulnerable URLs:")
    for r in results[:10]:
        if r['Security Status'] == 'PUBLIC':
            curl_info = f" [{r.get('Curl Status', 'N/A')}]" if VERIFY_URLS else ""
            print(f"  - {r['URL Path']} -> {r['View Function']}{curl_info}")

print(f"\n💡 Tip: Run with --verify-urls --base-url YOUR_URL to verify URLs on production")
print(f"{'='*80}\n")
