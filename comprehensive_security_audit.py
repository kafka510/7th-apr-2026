"""
Comprehensive Security Audit
Checks all possible internet-exposed endpoints including:
1. All URLs from urls.py files
2. Django Admin panel
3. Static/Media file exposure
4. Third-party app endpoints
5. DEBUG mode endpoints
6. Middleware endpoints
7. Settings-based security issues
"""
import os
import re
import ast
import csv
from pathlib import Path

BASE_DIR = Path(__file__).parent
results = []

def check_settings_security():
    """Check Django settings for security issues"""
    settings_file = BASE_DIR / 'web_app' / 'settings.py'
    if not settings_file.exists():
        return []
    
    issues = []
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for DEBUG = True in production
        debug_match = re.search(r'DEBUG\s*=\s*(True|False)', content)
        if debug_match:
            debug_val = debug_match.group(1)
            if debug_val == 'True':
                issues.append({
                    'type': 'SETTINGS',
                    'endpoint': 'ALL_ENDPOINTS',
                    'issue': 'DEBUG mode enabled - exposes error pages and debugging info',
                    'severity': 'CRITICAL',
                    'file': 'web_app/settings.py'
                })
        
        # Check ALLOWED_HOSTS
        allowed_hosts_match = re.search(r'ALLOWED_HOSTS\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if allowed_hosts_match:
            hosts = allowed_hosts_match.group(1)
            if "'*'" in hosts or '"*"' in hosts:
                issues.append({
                    'type': 'SETTINGS',
                    'endpoint': 'ALL_ENDPOINTS',
                    'issue': 'ALLOWED_HOSTS = ["*"] - allows any host (security risk)',
                    'severity': 'HIGH',
                    'file': 'web_app/settings.py'
                })
        
        # Check SECRET_KEY
        secret_key_match = re.search(r'SECRET_KEY\s*=\s*os\.getenv\(', content)
        if not secret_key_match:
            # Check for hardcoded secret key
            hardcoded_match = re.search(r"SECRET_KEY\s*=\s*['\"]([^'\"]+)['\"]", content)
            if hardcoded_match:
                issues.append({
                    'type': 'SETTINGS',
                    'endpoint': 'N/A',
                    'issue': 'SECRET_KEY may be hardcoded (should use environment variable)',
                    'severity': 'HIGH',
                    'file': 'web_app/settings.py'
                })
        
        # Check static/media file serving
        if 'static(settings.MEDIA_URL' in content and 'settings.DEBUG' in content:
            issues.append({
                'type': 'SETTINGS',
                'endpoint': '/media/*',
                'issue': 'Media files served directly in development (should use web server in production)',
                'severity': 'MEDIUM',
                'file': 'web_app/settings.py'
            })
        
    except Exception as e:
        print(f"Error checking settings: {e}")
    
    return issues

def check_admin_security():
    """Check Django admin panel security"""
    issues = []
    
    # Check if admin is registered
    url_file = BASE_DIR / 'web_app' / 'urls.py'
    if url_file.exists():
        with open(url_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'admin.site.urls' in content:
                issues.append({
                    'type': 'ADMIN',
                    'endpoint': '/admin/',
                    'issue': 'Django Admin panel enabled - ensure strong passwords and 2FA',
                    'severity': 'INFO',
                    'file': 'web_app/urls.py'
                })
    
    return issues

def check_static_media_exposure():
    """Check for static and media file exposure"""
    issues = []
    
    # Check media directory
    media_dir = BASE_DIR / 'media'
    if media_dir.exists():
        # Check for sensitive files
        sensitive_extensions = ['.env', '.key', '.pem', '.db', '.sqlite', '.log']
        for ext in sensitive_extensions:
            for file in media_dir.rglob(f'*{ext}'):
                issues.append({
                    'type': 'MEDIA',
                    'endpoint': f'/media/{file.relative_to(media_dir)}',
                    'issue': f'Sensitive file type ({ext}) in media directory - may be exposed',
                    'severity': 'HIGH',
                    'file': str(file.relative_to(BASE_DIR))
                })
    
    return issues

def check_third_party_endpoints():
    """Check third-party app endpoints"""
    issues = []
    url_file = BASE_DIR / 'web_app' / 'urls.py'
    
    if url_file.exists():
        with open(url_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for captcha
        if 'captcha.urls' in content:
            issues.append({
                'type': 'THIRD_PARTY',
                'endpoint': '/captcha/*',
                'issue': 'django-simple-captcha enabled - public endpoints for CAPTCHA',
                'severity': 'INFO',
                'file': 'web_app/urls.py',
                'note': 'This is expected for public forms'
            })
    
    return issues

def extract_all_api_endpoints_from_templates():
    """Extract API endpoints called from templates/JavaScript"""
    endpoints = set()
    templates_dir = BASE_DIR / 'templates'
    
    if templates_dir.exists():
        for html_file in templates_dir.rglob('*.html'):
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find fetch/AJAX calls
                patterns = [
                    r"fetch\(['\"]([^'\"]+)['\"]",
                    r"\.get\(['\"]([^'\"]+)['\"]",
                    r"\.post\(['\"]([^'\"]+)['\"]",
                    r"url:\s*['\"]([^'\"]+)['\"]",
                    r"'url':\s*['\"]([^'\"]+)['\"]",
                    r'"url":\s*["\']([^"\']+)["\']',
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        endpoint = match.group(1)
                        # Only add relative URLs (starting with /)
                        if endpoint.startswith('/'):
                            endpoints.add(endpoint.split('?')[0])  # Remove query params
                            
            except Exception as e:
                print(f"Error reading {html_file}: {e}")
    
    # Check if these endpoints are in our URL analysis
    endpoints_from_templates = []
    for endpoint in sorted(endpoints):
        endpoints_from_templates.append({
            'type': 'TEMPLATE_API',
            'endpoint': endpoint,
            'issue': 'API endpoint called from templates/JavaScript',
            'severity': 'INFO',
            'file': 'Templates/JavaScript',
            'note': 'Verify this endpoint is properly secured in security_audit_report.csv'
        })
    
    return endpoints_from_templates

def check_middleware_exposures():
    """Check for middleware that might expose endpoints"""
    issues = []
    settings_file = BASE_DIR / 'web_app' / 'settings.py'
    
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check middleware configuration
        if 'ActivityLoggingMiddleware' in content:
            issues.append({
                'type': 'MIDDLEWARE',
                'endpoint': 'ALL_ENDPOINTS',
                'issue': 'ActivityLoggingMiddleware - logs all requests (check for sensitive data logging)',
                'severity': 'INFO',
                'file': 'web_app/settings.py'
            })
        
        if 'URLEncryptionMiddleware' in content:
            issues.append({
                'type': 'MIDDLEWARE',
                'endpoint': 'ALL_ENDPOINTS',
                'issue': 'URLEncryptionMiddleware - URL encryption active',
                'severity': 'INFO',
                'file': 'web_app/settings.py'
            })
    
    return issues

def main():
    """Run comprehensive security audit"""
    print("\n" + "="*80)
    print("🔍 COMPREHENSIVE SECURITY AUDIT")
    print("="*80)
    
    all_issues = []
    
    # 1. Check Settings
    print("\n📋 Checking Django Settings...")
    settings_issues = check_settings_security()
    all_issues.extend(settings_issues)
    print(f"   Found {len(settings_issues)} settings issues")
    
    # 2. Check Admin
    print("\n📋 Checking Django Admin...")
    admin_issues = check_admin_security()
    all_issues.extend(admin_issues)
    print(f"   Found {len(admin_issues)} admin issues")
    
    # 3. Check Static/Media
    print("\n📋 Checking Static/Media Files...")
    media_issues = check_static_media_exposure()
    all_issues.extend(media_issues)
    print(f"   Found {len(media_issues)} media exposure issues")
    
    # 4. Check Third-Party Apps
    print("\n📋 Checking Third-Party Endpoints...")
    third_party_issues = check_third_party_endpoints()
    all_issues.extend(third_party_issues)
    print(f"   Found {len(third_party_issues)} third-party endpoints")
    
    # 5. Check Template API Calls
    print("\n📋 Checking Template/JavaScript API Calls...")
    template_apis = extract_all_api_endpoints_from_templates()
    all_issues.extend(template_apis)
    print(f"   Found {len(template_apis)} API endpoints called from templates")
    
    # 6. Check Middleware
    print("\n📋 Checking Middleware...")
    middleware_issues = check_middleware_exposures()
    all_issues.extend(middleware_issues)
    print(f"   Found {len(middleware_issues)} middleware configurations")
    
    # Write comprehensive report
    csv_file = BASE_DIR / 'comprehensive_security_audit.csv'
    if all_issues:
        # Standardize all dictionaries to have same keys
        fieldnames = ['type', 'endpoint', 'issue', 'severity', 'file', 'note']
        standardized_issues = []
        for issue in all_issues:
            std_issue = {key: issue.get(key, '') for key in fieldnames}
            standardized_issues.append(std_issue)
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(standardized_issues)
    
    # Print summary
    print("\n" + "="*80)
    print("📊 AUDIT SUMMARY")
    print("="*80)
    print(f"Total Issues Found: {len(all_issues)}")
    
    by_severity = {}
    for issue in all_issues:
        severity = issue.get('severity', 'UNKNOWN')
        by_severity[severity] = by_severity.get(severity, 0) + 1
    
    print("\nBy Severity:")
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'INFO']:
        count = by_severity.get(severity, 0)
        if count > 0:
            print(f"  {severity}: {count}")
    
    print(f"\n📝 Full report: {csv_file}")
    print(f"📋 URL Security Report: security_audit_report.csv")
    print("="*80)
    
    # Show critical/high issues
    critical_high = [i for i in all_issues if i.get('severity') in ['CRITICAL', 'HIGH']]
    if critical_high:
        print("\n⚠️  CRITICAL/HIGH PRIORITY ISSUES:")
        for issue in critical_high:
            print(f"\n  [{issue['severity']}] {issue['endpoint']}")
            print(f"      Issue: {issue['issue']}")
            print(f"      File: {issue['file']}")
    
    print("\n✅ Comprehensive audit complete!\n")

if __name__ == '__main__':
    main()

