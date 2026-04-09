"""
Convenience script to run both security audit scripts in sequence

Usage:
    python run_security_audit.py [--base-url BASE_URL] [--verify-urls] [--skip-check]

This script runs:
1. security_audit_analyzer.py - Generates CSV report
2. check_vulnerable_urls.py - Displays formatted analysis

Options:
    --base-url BASE_URL    Base URL for curl verification
    --verify-urls          Enable curl-based URL verification
    --skip-check           Skip the vulnerable URLs check (only generate CSV)
"""
import subprocess
import sys
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*80}")
    print(f"🔍 {description}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(cmd, check=True, cwd=BASE_DIR)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running command: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Script not found. Make sure you're in the project root directory.")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Run complete security audit (analyzer + checker)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic audit (local)
  python run_security_audit.py --verify-urls

  # Production audit
  python run_security_audit.py --base-url https://your-production.com --verify-urls

  # Generate CSV only
  python run_security_audit.py --skip-check
        """
    )
    
    parser.add_argument(
        '--base-url',
        default='http://localhost:8000',
        help='Base URL for curl verification (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--verify-urls',
        action='store_true',
        help='Enable curl-based URL verification'
    )
    parser.add_argument(
        '--skip-check',
        action='store_true',
        help='Skip vulnerable URLs check (only generate CSV report)'
    )
    parser.add_argument(
        '--skip-curl',
        action='store_true',
        help='Skip curl verification even if enabled'
    )
    
    args = parser.parse_args()
    
    # Build command arguments
    analyzer_args = ['python', 'security_audit_analyzer.py']
    checker_args = ['python', 'check_vulnerable_urls.py']
    
    if args.base_url:
        analyzer_args.extend(['--base-url', args.base_url])
        checker_args.extend(['--base-url', args.base_url])
    
    if args.verify_urls:
        analyzer_args.append('--verify-urls')
        checker_args.append('--verify-urls')
    
    if args.skip_curl:
        analyzer_args.append('--skip-curl')
        checker_args.append('--skip-curl')
    
    # Step 1: Run analyzer
    print(f"\n{'='*80}")
    print(f"🚀 Starting Complete Security Audit")
    print(f"{'='*80}")
    print(f"Base URL: {args.base_url}")
    print(f"URL Verification: {'Enabled' if args.verify_urls and not args.skip_curl else 'Disabled'}")
    print(f"{'='*80}\n")
    
    success = run_command(
        analyzer_args,
        "Step 1/2: Generating Security Audit Report"
    )
    
    if not success:
        print("\n❌ Failed to generate security audit report. Exiting.")
        sys.exit(1)
    
    # Step 2: Run checker (unless skipped)
    if not args.skip_check:
        success = run_command(
            checker_args,
            "Step 2/2: Analyzing Vulnerable URLs"
        )
        
        if not success:
            print("\n⚠️  CSV report generated, but failed to run vulnerable URLs check.")
            print("   You can manually run: python check_vulnerable_urls.py")
            sys.exit(1)
    else:
        print(f"\n{'='*80}")
        print("⏭️  Skipping vulnerable URLs check (--skip-check)")
        print(f"{'='*80}\n")
        print("💡 To check vulnerable URLs, run:")
        print(f"   python check_vulnerable_urls.py --base-url {args.base_url}")
        if args.verify_urls:
            print("   python check_vulnerable_urls.py --verify-urls")
    
    # Final summary
    csv_file = BASE_DIR / 'security_audit_report.csv'
    print(f"\n{'='*80}")
    print("✅ Security Audit Complete!")
    print(f"{'='*80}")
    print(f"📝 CSV Report: {csv_file}")
    print(f"📋 Usage Guide: SECURITY_AUDIT_USAGE.md")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()

