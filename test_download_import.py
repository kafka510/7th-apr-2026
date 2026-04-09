import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')
django.setup()

try:
    print("Attempting to import download_views...")
    from main.views import download_views
    print("✓ download_views imported successfully")
    
    print("\nChecking for download_page...")
    if hasattr(download_views, 'download_page'):
        print("✓ download_page found in download_views")
    else:
        print("✗ download_page NOT found in download_views")
        print("\nAvailable attributes:")
        import inspect
        attrs = [name for name in dir(download_views) if not name.startswith('_')]
        for attr in attrs[:20]:  # Show first 20
            print(f"  - {attr}")
    
    print("\nAttempting direct import...")
    from main.views.download_views import download_page
    print("✓ download_page imported directly")
    
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

