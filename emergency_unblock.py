#!/usr/bin/env python3
"""
Emergency IP Unblock Script
Run this script if you get blocked and need immediate access
"""

import os
import sys
import django
from pathlib import Path
import requests
import json
from urllib3.exceptions import InsecureRequestWarning

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')
django.setup()

from main.models import BlockedIP, IPBlockingLog, UserBlockingLog, BlockedUser
from main.middleware.realtime_ip_blocker import realtime_blocker
from django.utils import timezone
from django.contrib.auth.models import User

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def get_my_ip():
    """Get your current public IP address"""
    
    return input("Please enter your IP address: ")

def get_username():
    """Get username for unblocking"""
    return input("Please enter the username to unblock: ")

# Removed API functions - they don't work in emergency situations

def run_management_command(command, *args):
    """Run a Django management command"""
    try:
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        # Capture output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            call_command(command, *args)
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            return True, output
        except Exception as e:
            sys.stdout = old_stdout
            return False, str(e)
    except Exception as e:
        return False, str(e)

def force_cache_reload():
    """Force the running middleware to reload its cache by creating a signal file"""
    try:
        import os
        import time
        
        # Create a signal file that the middleware can check
        signal_file = "reload_cache_signal.txt"
        
        # Write current timestamp to signal file
        with open(signal_file, 'w') as f:
            f.write(str(time.time()))
        
        print("🔄 Created cache reload signal file")
        
        # Also try to run the management command if possible
        print("🔄 Attempting to run cache reload command...")
        success, output = run_management_command('reload_blocking_cache', '--force')
        
        if success:
            print("✅ Cache reload command executed successfully")
            print(f"   Output: {output}")
        else:
            print(f"⚠️  Cache reload command failed: {output}")
            print("   The signal file method should still work")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating cache reload signal: {str(e)}")
        return False

def emergency_unblock_ip_immediate(ip_address=None, reason="Emergency unblock", nuclear=False):
    """Emergency unblock with immediate effect - forces cache reload"""
    if not ip_address:
        ip_address = get_my_ip()
    
    print(f"🚀 EMERGENCY IP UNBLOCK (IMMEDIATE): {ip_address}")
    print("=" * 60)
    print("This will unblock the IP and force the middleware to reload its cache.")
    
    try:
        # 1. Clear ALL database blocks for this IP
        print("1. Clearing database blocks...")
        blocked_ips = BlockedIP.objects.filter(ip_address=ip_address, status='active')
        if blocked_ips.exists():
            blocked_ips.update(status='inactive', updated_at=timezone.now())
            print(f"   ✅ Deactivated {blocked_ips.count()} database blocks")
        else:
            print("   ℹ️  No active database blocks found")
        
        # 2. Invalidate cache (will reload from database on next access)
        print("2. Invalidating cache...")
        realtime_blocker._invalidate_cache()
        print("   ✅ Cache invalidated (will reload from database)")
        
        # 3. Nuclear option - clear ALL IP blocks
        if nuclear:
            print("3. NUCLEAR OPTION - Clearing ALL IP blocks...")
            all_blocked = BlockedIP.objects.filter(status='active')
            if all_blocked.exists():
                all_blocked.update(status='inactive', updated_at=timezone.now())
                print(f"   ✅ Deactivated {all_blocked.count()} total IP blocks")
            realtime_blocker._invalidate_cache()
            print("   ✅ Cache invalidated")
        
        # 4. Clear failed login attempts for affected users
        print("4. Clearing failed login attempts for affected users...")
        from accounts.models import LoginAttempt
        from main.models import UserBlockingLog
        
        # Find users blocked from this IP
        affected_usernames = UserBlockingLog.objects.filter(
            ip_address=ip_address,
            status='active'
        ).values_list('user__username', flat=True).distinct()
        
        cleared_count = 0
        for username in affected_usernames:
            if username:
                LoginAttempt.clear_attempts(username)
                cleared_count += 1
        
        if cleared_count > 0:
            print(f"   ✅ Cleared login attempts for {cleared_count} user(s)")
        else:
            print("   ℹ️  No users found associated with this IP")
        
        # 5. Force cache reload in running middleware
        print("5. Forcing middleware cache reload...")
        if force_cache_reload():
            print("   ✅ Cache reload signal sent")
        else:
            print("   ⚠️  Cache reload signal failed, but database changes are saved")
        
        # 6. Update existing active log entries (instead of creating new)
        print("6. Updating log entries...")
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            updated_count = IPBlockingLog.objects.filter(
                ip_address=ip_address,
                status='active'
            ).update(
                status='unblocked',
                unblocked_by=admin_user,
                unblocked_at=timezone.now(),
                unblock_reason=reason
            )
            if updated_count > 0:
                print(f"   ✅ Updated {updated_count} log entry(ies)")
            else:
                print("   ℹ️  No active log entries found to update")
        except Exception as e:
            print(f"   ⚠️  Could not create log entry: {str(e)}")
        
        print(f"\n🎉 SUCCESS: IP {ip_address} has been unblocked!")
        if nuclear:
            print("🚨 NUCLEAR OPTION: All IP blocks have been cleared!")
        print("🔄 The middleware should reload its cache automatically.")
        print("✅ You should now be able to access the application!")
        return True
        
    except Exception as e:
        print(f"❌ Error during emergency unblock: {str(e)}")
        return False

def emergency_unblock_user_immediate(username=None, reason="Emergency user unblock", nuclear=False):
    """Emergency user unblock with immediate effect - forces cache reload"""
    if not username:
        username = get_username()
    
    print(f"🚀 EMERGENCY USER UNBLOCK (IMMEDIATE): {username}")
    print("=" * 60)
    print("This will unblock the user and force the middleware to reload its cache.")
    
    try:
        # 1. Check if user exists
        try:
            user = User.objects.get(username=username)
            print(f"Found user: {username} ({user.email})")
        except User.DoesNotExist:
            print(f"❌ User '{username}' not found")
            return False
        
        # 2. Fix Django User model
        print("1. Fixing Django User model...")
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print("   ✅ User account fully activated (active, staff, superuser)")
        
        # Clear failed login attempts
        from accounts.models import LoginAttempt
        LoginAttempt.clear_attempts(username)
        print("   ✅ Cleared failed login attempts from database")
        
        # 3. Clear BlockedUser table
        print("2. Clearing BlockedUser table...")
        blocked_users = BlockedUser.objects.filter(user=user, status='active')
        if blocked_users.exists():
            blocked_users.update(status='inactive', updated_at=timezone.now())
            print(f"   ✅ Deactivated {blocked_users.count()} BlockedUser records")
        else:
            print("   ℹ️  No active BlockedUser records found")
        
        # 4. Invalidate cache (will reload from database on next access)
        print("3. Invalidating cache...")
        realtime_blocker._invalidate_cache()
        print("   ✅ Cache invalidated (will reload from database)")
        
        # 5. Nuclear option - clear ALL user blocks
        if nuclear:
            print("4. NUCLEAR OPTION - Clearing ALL user blocks...")
            all_blocked_users = BlockedUser.objects.filter(status='active')
            if all_blocked_users.exists():
                all_blocked_users.update(status='inactive', updated_at=timezone.now())
                print(f"   ✅ Deactivated {all_blocked_users.count()} total user blocks")
            realtime_blocker._invalidate_cache()
            print("   ✅ Cache invalidated")
            
            # Make ALL users admin
            User.objects.all().update(is_active=True, is_staff=True, is_superuser=True)
            print("   ✅ Made ALL users admin")
        
        # 6. Force cache reload in running middleware
        print("5. Forcing middleware cache reload...")
        if force_cache_reload():
            print("   ✅ Cache reload signal sent")
        else:
            print("   ⚠️  Cache reload signal failed, but database changes are saved")
        
        # 7. Update existing active user log entries (instead of creating new)
        print("6. Updating log entries...")
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            updated_count = UserBlockingLog.objects.filter(
                user=user,
                status='active'
            ).update(
                status='unblocked',
                unblocked_by=admin_user,
                unblocked_at=timezone.now(),
                unblock_reason=reason
            )
            if updated_count > 0:
                print(f"   ✅ Updated {updated_count} log entry(ies)")
            else:
                print("   ℹ️  No active log entries found to update")
        except Exception as e:
            print(f"   ⚠️  Could not create log entry: {str(e)}")
        
        print(f"\n🎉 SUCCESS: User '{username}' has been unblocked!")
        if nuclear:
            print("🚨 NUCLEAR OPTION: All user blocks have been cleared!")
        print("🔄 The middleware should reload its cache automatically.")
        print("✅ The user should now be able to access the application!")
        return True
        
    except Exception as e:
        print(f"❌ Error during emergency user unblock: {str(e)}")
        return False

def emergency_unblock_ip(ip_address=None, reason="Emergency unblock", nuclear=False):
    """Emergency unblock function for IP addresses - handles ALL blocking mechanisms"""
    if not ip_address:
        ip_address = get_my_ip()
    
    print(f"🚀 EMERGENCY IP UNBLOCK: {ip_address}")
    print("=" * 50)
    
    try:
        # 1. Clear ALL database blocks for this IP
        print("1. Clearing database blocks...")
        blocked_ips = BlockedIP.objects.filter(ip_address=ip_address, status='active')
        if blocked_ips.exists():
            blocked_ips.update(status='inactive', updated_at=timezone.now())
            print(f"   ✅ Deactivated {blocked_ips.count()} database blocks")
        else:
            print("   ℹ️  No active database blocks found")
        
        # 2. Invalidate cache (will reload from database on next access)
        print("2. Invalidating cache...")
        realtime_blocker._invalidate_cache()
        print("   ✅ Cache invalidated (will reload from database)")
        
        # 3. Nuclear option - clear ALL IP blocks
        if nuclear:
            print("3. NUCLEAR OPTION - Clearing ALL IP blocks...")
            all_blocked = BlockedIP.objects.filter(status='active')
            if all_blocked.exists():
                all_blocked.update(status='inactive', updated_at=timezone.now())
                print(f"   ✅ Deactivated {all_blocked.count()} total IP blocks")
            realtime_blocker._invalidate_cache()
            print("   ✅ Cache invalidated")
        
        # 4. Clear failed login attempts for affected users
        print("4. Clearing failed login attempts for affected users...")
        from accounts.models import LoginAttempt
        from main.models import UserBlockingLog
        
        # Find users blocked from this IP
        affected_usernames = UserBlockingLog.objects.filter(
            ip_address=ip_address,
            status='active'
        ).values_list('user__username', flat=True).distinct()
        
        cleared_count = 0
        for username in affected_usernames:
            if username:
                LoginAttempt.clear_attempts(username)
                cleared_count += 1
        
        if cleared_count > 0:
            print(f"   ✅ Cleared login attempts for {cleared_count} user(s)")
        else:
            print("   ℹ️  No users found associated with this IP")
        
        # 5. Update existing active log entries (instead of creating new)
        print("5. Updating log entries...")
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            updated_count = IPBlockingLog.objects.filter(
                    ip_address=ip_address,
                status='active'
            ).update(
                    status='unblocked',
                    unblocked_by=admin_user,
                    unblocked_at=timezone.now(),
                unblock_reason=reason
            )
            if updated_count > 0:
                print(f"   ✅ Updated {updated_count} log entry(ies)")
            else:
                print("   ℹ️  No active log entries found to update")
        except Exception as e:
            print(f"   ⚠️  Could not update log entry: {e}")
        
        print(f"\n🎉 SUCCESS: IP {ip_address} has been unblocked!")
        if nuclear:
            print("🚨 NUCLEAR OPTION: All IP blocks have been cleared!")
        print("You should now be able to access the application.")
        
        return True
            
    except Exception as e:
        print(f"❌ ERROR: Failed to unblock IP: {e}")
        return False

def emergency_unblock_user(username=None, reason="Emergency unblock", nuclear=False):
    """Emergency unblock function for users - handles ALL blocking mechanisms"""
    if not username:
        username = get_username()
    
    print(f"🚀 EMERGENCY USER UNBLOCK: {username}")
    print("=" * 50)
        
    try:
        # Check if user exists
        try:
            user = User.objects.get(username=username)
            print(f"Found user: {user.get_full_name() or user.username} ({user.email})")
        except User.DoesNotExist:
            print(f"❌ ERROR: User '{username}' does not exist")
            return False
    
        # 1. Fix Django User model
        print("1. Fixing Django User model...")
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print("   ✅ User account fully activated (active, staff, superuser)")
        
        # Clear failed login attempts
        from accounts.models import LoginAttempt
        LoginAttempt.clear_attempts(username)
        print("   ✅ Cleared failed login attempts from database")
        
        # 2. Clear BlockedUser table
        print("2. Clearing BlockedUser table...")
        blocked_users = BlockedUser.objects.filter(user=user, status='active')
        if blocked_users.exists():
            blocked_users.update(status='inactive', updated_at=timezone.now())
            print(f"   ✅ Deactivated {blocked_users.count()} BlockedUser records")
        else:
            print("   ℹ️  User not found in BlockedUser table")
        
        # 3. Invalidate cache (will reload from database on next access)
        print("3. Invalidating cache...")
        realtime_blocker._invalidate_cache()
        print("   ✅ Cache invalidated (will reload from database)")
        
        # 4. Nuclear option - clear ALL user blocks
        if nuclear:
            print("4. NUCLEAR OPTION - Clearing ALL user blocks...")
            all_blocked_users = BlockedUser.objects.filter(status='active')
            if all_blocked_users.exists():
                all_blocked_users.update(status='inactive', updated_at=timezone.now())
                print(f"   ✅ Deactivated {all_blocked_users.count()} total user blocks")
            realtime_blocker._invalidate_cache()
            print("   ✅ Cache invalidated")
            
            # Make ALL users admin
            User.objects.all().update(is_active=True, is_staff=True, is_superuser=True)
            print("   ✅ Made ALL users admin")
        
        # 5. Update existing active user log entries (instead of creating new)
        print("5. Updating log entries...")
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            updated_count = UserBlockingLog.objects.filter(
                    user=user,
                status='active'
            ).update(
                    status='unblocked',
                    unblocked_by=admin_user,
                    unblocked_at=timezone.now(),
                unblock_reason=reason
            )
            if updated_count > 0:
                print(f"   ✅ Updated {updated_count} log entry(ies)")
            else:
                print("   ℹ️  No active log entries found to update")
        except Exception as e:
            print(f"   ⚠️  Could not update log entry: {e}")
        
        print(f"\n🎉 SUCCESS: User '{username}' has been unblocked!")
        if nuclear:
            print("🚨 NUCLEAR OPTION: All user blocks have been cleared!")
        print("The user should now be able to access the application.")
        
        return True
            
    except Exception as e:
        print(f"❌ ERROR: Failed to unblock user: {e}")
        return False

def check_ip_blocking_status(ip_address=None):
    """Check if IP is currently blocked"""
    if not ip_address:
        ip_address = get_my_ip()
    
    print(f"Checking blocking status for IP: {ip_address}")
    
    # Check database
    try:
        blocked_ip = BlockedIP.objects.get(ip_address=ip_address, status='active')
        print(f"🔴 BLOCKED in database: {blocked_ip.reason}")
        print(f"   Blocked at: {blocked_ip.created_at}")
        print(f"   Blocked by: {blocked_ip.blocked_by}")
    except BlockedIP.DoesNotExist:
        print("✅ Not blocked in database")
    
    # Check memory cache
    if ip_address in realtime_blocker.blocked_ips:
        print("🔴 BLOCKED in memory cache")
    else:
        print("✅ Not blocked in memory cache")

def check_user_status(username=None):
    """Check if user is currently blocked"""
    if not username:
        username = get_username()
    
    print(f"Checking user status for: {username}")
    
    try:
        user = User.objects.get(username=username)
        print(f"User found: {user.get_full_name() or user.username} ({user.email})")
        print(f"Active: {'✅ Yes' if user.is_active else '🔴 No'}")
        print(f"Staff: {'✅ Yes' if user.is_staff else '❌ No'}")
        print(f"Superuser: {'✅ Yes' if user.is_superuser else '❌ No'}")
        print(f"Last login: {user.last_login or 'Never'}")
        
        if not user.is_active:
            print("🔴 USER IS BLOCKED - Account is inactive")
        elif not user.is_staff and not user.is_superuser:
            print("⚠️  User may have limited access (not staff/superuser)")
        else:
            print("✅ User appears to have full access")
            
    except User.DoesNotExist:
        print(f"❌ User '{username}' does not exist")

def emergency_unblock_everything(ip_address=None, username=None, reason="Emergency unblock everything"):
    """Nuclear option - unblock everything"""
    print("🚨 NUCLEAR OPTION: UNBLOCKING EVERYTHING")
    print("=" * 60)
    
    if not ip_address:
        ip_address = get_my_ip()
    if not username:
        username = get_username()
    
    print(f"Target IP: {ip_address}")
    print(f"Target User: {username}")
    print()
    
    # Unblock IP with nuclear option
    print("🔥 Unblocking IP with nuclear option...")
    emergency_unblock_ip(ip_address, reason, nuclear=True)
    
    print()
    
    # Unblock user with nuclear option
    print("🔥 Unblocking user with nuclear option...")
    emergency_unblock_user(username, reason, nuclear=True)
    
    print()
    print("🚨 NUCLEAR OPTION COMPLETED!")
    print("All blocking mechanisms have been cleared.")
    print("This should resolve any persistent blocking issues.")

def clear_all_blocks():
    """Clear all blocks from all systems"""
    print("🧹 CLEARING ALL BLOCKS FROM ALL SYSTEMS")
    print("=" * 60)
    
    # Clear all IP blocks
    print("1. Clearing ALL IP blocks...")
    ip_count = BlockedIP.objects.filter(status='active').count()
    BlockedIP.objects.filter(status='active').update(status='inactive', updated_at=timezone.now())
    realtime_blocker._invalidate_cache()
    print(f"   ✅ Cleared {ip_count} IP blocks and invalidated cache")
    
    # Clear all user blocks
    print("2. Clearing ALL user blocks...")
    user_count = BlockedUser.objects.filter(status='active').count()
    BlockedUser.objects.filter(status='active').update(status='inactive', updated_at=timezone.now())
    realtime_blocker._invalidate_cache()
    print(f"   ✅ Cleared {user_count} user blocks and invalidated cache")
    
    # Make all users admin
    print("3. Making ALL users admin...")
    total_users = User.objects.count()
    User.objects.all().update(is_active=True, is_staff=True, is_superuser=True)
    print(f"   ✅ Made {total_users} users admin")
    
    print(f"\n🎉 ALL BLOCKS CLEARED!")
    print("Every blocking mechanism has been disabled.")

def diagnose_blocking(ip_address=None, username=None):
    """Diagnose what's causing the blocking"""
    print("🔍 DIAGNOSING BLOCKING ISSUES")
    print("=" * 60)
    
    if not ip_address:
        ip_address = get_my_ip()
    if not username:
        username = get_username()
    
    print(f"Diagnosing for IP: {ip_address}, User: {username}")
    print()
    
    # Check IP blocking
    print("IP Blocking Check:")
    try:
        blocked_ip = BlockedIP.objects.get(ip_address=ip_address, status='active')
        print(f"   🔴 BLOCKED in database: {blocked_ip.reason}")
    except BlockedIP.DoesNotExist:
        print("   ✅ Not blocked in database")
    
    if ip_address in realtime_blocker.blocked_ips:
        print("   🔴 BLOCKED in memory cache")
    else:
        print("   ✅ Not blocked in memory cache")
    
    # Check user blocking
    print("\nUser Blocking Check:")
    try:
        user = User.objects.get(username=username)
        print(f"   User found: {user.username}")
        print(f"   Active: {'✅ Yes' if user.is_active else '🔴 No'}")
        print(f"   Staff: {'✅ Yes' if user.is_staff else '❌ No'}")
        print(f"   Superuser: {'✅ Yes' if user.is_superuser else '❌ No'}")
        
        try:
            blocked_user = BlockedUser.objects.get(user=user, status='active')
            print(f"   🔴 BLOCKED in BlockedUser table: {blocked_user.reason}")
        except BlockedUser.DoesNotExist:
            print("   ✅ Not blocked in BlockedUser table")
        
        if username in realtime_blocker.blocked_users:
            print("   🔴 BLOCKED in memory cache")
        else:
            print("   ✅ Not blocked in memory cache")
            
    except User.DoesNotExist:
        print(f"   ❌ User '{username}' does not exist")
    
    print(f"\n💡 If still blocked, the issue might be:")
    print("   - Nginx-level blocking (rate limiting, fail2ban)")
    print("   - Custom security middleware")
    print("   - Browser cache (try incognito mode)")
    print("   - Network-level blocking")
    print("   - Cached blocking response")

if __name__ == "__main__":
    print("🚨 EMERGENCY UNBLOCK SCRIPT 🚨")
    print("=" * 40)
    
    import sys
    
    # Check command line arguments
    if len(sys.argv) > 1:
        unblock_type = sys.argv[1].lower()
        
        if unblock_type in ['immediate', '--immediate', 'ip', '--ip']:
            # Immediate IP unblocking
            ip_address = sys.argv[2] if len(sys.argv) > 2 else None
            nuclear = '--nuclear' in sys.argv or '--nuke' in sys.argv
            if ip_address:
                emergency_unblock_ip_immediate(ip_address, "Emergency immediate unblock", nuclear)
            else:
                print("Usage: python emergency_unblock.py immediate [IP_ADDRESS] [--nuclear]")
            
        elif unblock_type in ['user', '--user', '--username']:
            # Immediate user unblocking
            username = sys.argv[2] if len(sys.argv) > 2 else None
            nuclear = '--nuclear' in sys.argv or '--nuke' in sys.argv
            if username:
                emergency_unblock_user_immediate(username, "Emergency immediate user unblock", nuclear)
            else:
                print("Usage: python emergency_unblock.py user [USERNAME] [--nuclear]")
            
        elif unblock_type in ['everything', '--everything', 'all', '--all']:
            # Unblock everything
            ip_address = sys.argv[2] if len(sys.argv) > 2 else None
            username = sys.argv[3] if len(sys.argv) > 3 else None
            reason = sys.argv[4] if len(sys.argv) > 4 else "Emergency unblock everything via command line"
            emergency_unblock_everything(ip_address, username, reason)
            
        elif unblock_type in ['clear', '--clear', 'clearall', '--clearall']:
            # Clear all blocks
            clear_all_blocks()
            
        elif unblock_type in ['diagnose', '--diagnose', 'debug', '--debug']:
            # Diagnose blocking
            ip_address = sys.argv[2] if len(sys.argv) > 2 else None
            username = sys.argv[3] if len(sys.argv) > 3 else None
            diagnose_blocking(ip_address, username)
            
        elif unblock_type in ['check', '--check', 'status']:
            # Check status
            check_type = sys.argv[2].lower() if len(sys.argv) > 2 else None
            if check_type in ['ip', '--ip']:
                ip_address = sys.argv[3] if len(sys.argv) > 3 else None
                check_ip_blocking_status(ip_address)
            elif check_type in ['user', '--user', '--username']:
                username = sys.argv[3] if len(sys.argv) > 3 else None
                check_user_status(username)
            else:
                print("Usage: python emergency_unblock.py check [ip|user] [address|username]")
                
                
        else:
            # Legacy: treat first argument as IP address
            ip_address = sys.argv[1]
            reason = sys.argv[2] if len(sys.argv) > 2 else "Emergency unblock via command line"
            emergency_unblock_ip(ip_address, reason)
    else:
        # Interactive mode
        print("This script will help you unblock IP addresses or users.")
        print()
        print("Command line usage:")
        print("  python emergency_unblock.py immediate [IP_ADDRESS] [--nuclear]  # EMERGENCY IP ⭐")
        print("  python emergency_unblock.py user [USERNAME] [--nuclear]  # EMERGENCY USER ⭐")
        print("  python emergency_unblock.py everything [IP_ADDRESS] [USERNAME] [REASON]")
        print("  python emergency_unblock.py clear")
        print("  python emergency_unblock.py check ip [IP_ADDRESS]")
        print("  python emergency_unblock.py check user [USERNAME]")
        print()
        
        # Ask what to do
        print("What would you like to do?")
        print("1. IMMEDIATE IP unblock (No web access needed) ⭐")
        print("2. IMMEDIATE User unblock (No web access needed) ⭐")
        print("3. Unblock everything (nuclear option)")
        print("4. Clear all blocks")
        print("5. Check IP blocking status")
        print("6. Check user status")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == '1':
            print("\n--- IMMEDIATE IP Unblock (No web access needed) ---")
            ip_address = input("Enter IP address to unblock: ").strip()
            if ip_address:
                nuclear = input("Use nuclear option? (clears ALL IP blocks) (y/N): ").lower() == 'y'
                emergency_unblock_ip_immediate(ip_address, "Emergency immediate unblock", nuclear)
            else:
                print("IP address is required")
                
        elif choice == '2':
            print("\n--- IMMEDIATE User Unblock (No web access needed) ---")
            username = input("Enter username to unblock: ").strip()
            if username:
                nuclear = input("Use nuclear option? (clears ALL user blocks) (y/N): ").lower() == 'y'
                emergency_unblock_user_immediate(username, "Emergency immediate user unblock", nuclear)
            else:
                print("Username is required")
                
        elif choice == '3':
            print("\n--- NUCLEAR OPTION: Unblock Everything ---")
            print("This will clear ALL blocking mechanisms for both IP and user.")
            response = input("Are you sure? This is a nuclear option! (y/N): ")
            if response.lower() == 'y':
                emergency_unblock_everything()
            else:
                print("Nuclear option cancelled.")
                
        elif choice == '4':
            print("\n--- Clear All Blocks ---")
            print("This will clear ALL blocks from ALL systems.")
            response = input("Are you sure? (y/N): ")
            if response.lower() == 'y':
                clear_all_blocks()
            else:
                print("Clear all blocks cancelled.")
                
        elif choice == '5':
            print("\n--- IP Status Check ---")
            check_ip_blocking_status()
            
        elif choice == '6':
            print("\n--- User Status Check ---")
            check_user_status()
            
        elif choice == '7':
            print("Exiting...")
            
        else:
            print("Invalid choice. Exiting...")