"""
Enhanced script to check vulnerable URLs from the security audit report
Now includes curl-based verification and better categorization

Usage:
    python check_vulnerable_urls.py [--base-url BASE_URL] [--verify-urls] [--csv-file FILE]

Options:
    --base-url BASE_URL    Base URL for curl verification (default: http://localhost:8000)
    --verify-urls          Enable curl-based URL verification
    --csv-file FILE        Path to CSV file (default: security_audit_report.csv)
    --skip-curl           Skip curl verification even if enabled
"""
import csv
import subprocess
import argparse
import os
from pathlib import Path
from urllib.parse import urljoin

BASE_DIR = Path(__file__).parent
DEFAULT_CSV_FILE = BASE_DIR / 'security_audit_report.csv'
BASE_URL = os.getenv('SECURITY_AUDIT_BASE_URL', 'http://localhost:8000')
VERIFY_URLS = False
SKIP_CURL = False

def verify_url_with_curl(url_path, base_url):
    """Verify URL accessibility using curl"""
    if SKIP_CURL:
        return None, None
    
    try:
        full_url = urljoin(base_url.rstrip('/') + '/', url_path.lstrip('/'))
        
        # Use curl to check if URL redirects to login (indicates protection)
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

def categorize_endpoint(url_info):
    """Categorize an endpoint based on its URL and view"""
    url = url_info.get('URL Path', '').lower()
    view = url_info.get('View Function', '').lower()
    security_status = url_info.get('Security Status', '')
    
    # Intentionally public endpoints
    if any(x in url for x in ['login', 'logout', 'register', 'password-reset', 'password_reset']):
        return 'auth', 'Authentication Endpoints (Intentional Public - OK)'
    
    if 'captcha' in url:
        return 'captcha', 'CAPTCHA Endpoints (Intentional Public - OK)'
    
    # Test/debug endpoints
    if any(x in url for x in ['csrf', 'test', 'debug', 'simple-csrf']):
        return 'test', 'Test/Debug Endpoints (Should Remove in Production)'
    
    # API endpoints
    if 'api/v1/auth/token' in url:
        return 'api_auth', 'API Authentication Endpoints (Check API Key Protection)'
    elif 'api/' in url:
        return 'api', 'API Endpoints (Check API Key Protection)'
    
    # Included modules
    if url_info.get('View Function') == 'INCLUDED_MODULE':
        return 'module', 'Included Modules (Check Individual Routes)'
    
    # Actually vulnerable
    if security_status == 'PUBLIC':
        return 'vulnerable', '⚠️ Potentially Vulnerable Endpoints'
    
    return 'other', 'Other Endpoints'

# Parse command line arguments
parser = argparse.ArgumentParser(description='Check Vulnerable URLs')
parser.add_argument('--base-url', default=BASE_URL, help=f'Base URL for verification (default: {BASE_URL})')
parser.add_argument('--verify-urls', action='store_true', help='Enable curl-based URL verification')
parser.add_argument('--csv-file', default=DEFAULT_CSV_FILE, help=f'Path to CSV file (default: {DEFAULT_CSV_FILE})')
parser.add_argument('--skip-curl', action='store_true', help='Skip curl verification')
args = parser.parse_args()

BASE_URL = args.base_url
VERIFY_URLS = args.verify_urls
CSV_FILE = Path(args.csv_file)
SKIP_CURL = args.skip_curl

if not CSV_FILE.exists():
    print("❌ CSV file not found!")
    print(f"   Expected: {CSV_FILE}")
    print("   Run 'python security_audit_analyzer.py' first to generate the report.")
    exit(1)

# Read CSV
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    data = list(reader)

# Filter vulnerable URLs
vulnerable = [r for r in data if r.get('Security Status', '') == 'PUBLIC']

print(f'\n{"="*80}')
print(f'⚠️  SECURITY AUDIT - VULNERABLE URLS CHECK')
print(f'{"="*80}')
print(f'CSV File: {CSV_FILE}')
print(f'Base URL: {BASE_URL}')
print(f'URL Verification: {"Enabled" if VERIFY_URLS and not SKIP_CURL else "Disabled"}')
print(f'Total URLs Analyzed: {len(data)}')
print(f'Vulnerable URLs (PUBLIC): {len(vulnerable)}')
print(f'{"="*80}\n')

if vulnerable:
    # Categorize vulnerabilities
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
    
    # Display categorized results
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
                
                # Show curl status if available
                curl_status = r.get('Curl Status', '')
                curl_details = r.get('Curl Details', '')
                
                print(f"  {i}. {url}")
                print(f"      View: {view} ({view_type})")
                if file_loc != 'Unknown':
                    print(f"      File: {file_loc}")
                
                # Show curl verification results
                if VERIFY_URLS and curl_status:
                    status_icon = '✅' if curl_status == 'PROTECTED' else '⚠️' if curl_status == 'ACCESSIBLE' else '❓'
                    print(f"      {status_icon} Curl: {curl_status} - {curl_details}")
                elif VERIFY_URLS and not SKIP_CURL:
                    # Verify on the fly if not in CSV
                    curl_status, curl_details = verify_url_with_curl(url, BASE_URL)
                    if curl_status:
                        status_icon = '✅' if curl_status == 'PROTECTED' else '⚠️' if curl_status == 'ACCESSIBLE' else '❓'
                        print(f"      {status_icon} Curl: {curl_status} - {curl_details}")
                
                # Show decorators if available
                decorators = r.get('Decorators', 'None')
                if decorators != 'None':
                    print(f"      Decorators: {decorators}")
                
                print()
    
    # Summary statistics
    print(f'\n{"="*80}')
    print("📊 Summary Statistics:")
    print(f"   Total Public Endpoints: {len(vulnerable)}")
    print(f"   Authentication Endpoints: {len(categories['auth'])}")
    print(f"   Test/Debug Endpoints: {len(categories['test'])}")
    print(f"   API Endpoints: {len(categories['api']) + len(categories['api_auth'])}")
    print(f"   Actually Vulnerable: {len(categories['vulnerable'])}")
    print(f"   Included Modules: {len(categories['module'])}")
    print(f'{"="*80}\n')
    
    # Recommendations
    if categories['vulnerable']:
        print("⚠️  RECOMMENDATIONS:")
        print("   1. Review the 'Potentially Vulnerable Endpoints' listed above")
        print("   2. Add authentication decorators (@login_required, @role_required, etc.)")
        print("   3. For class-based views, use LoginRequiredMixin or AccessControlMixin")
        print("   4. Remove or secure test/debug endpoints in production")
        print()
    
    if categories['test']:
        print("⚠️  TEST ENDPOINTS FOUND:")
        print("   Consider removing or securing these endpoints in production:")
        for r in categories['test']:
            print(f"   - {r.get('URL Path', 'N/A')}")
        print()
else:
    print("✅ No vulnerable URLs found! All endpoints are protected.")
    print()

print(f'{"="*80}')
print("📝 Full report: security_audit_report.csv")
print("📋 Summary: SECURITY_AUDIT_SUMMARY.md")
print(f'{"="*80}\n')

# Show how to run with verification
if not VERIFY_URLS:
    print("💡 Tip: Run with --verify-urls --base-url YOUR_URL to verify URLs")
    print("   Example: python check_vulnerable_urls.py --verify-urls --base-url https://your-production.com")
    print()
