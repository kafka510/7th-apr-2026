import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')

print("Setting up Django...")
django.setup()

print("\n=== Testing download_views import ===")
try:
    # Try importing the module directly
    import main.views.download_views as dv_module
    print("✓ Module imported")
    
    # Check what's actually in the module
    print(f"\nModule file: {dv_module.__file__}")
    print(f"Module name: {dv_module.__name__}")
    
    # Get all attributes
    all_attrs = dir(dv_module)
    functions = [attr for attr in all_attrs if not attr.startswith('_') and callable(getattr(dv_module, attr, None))]
    
    print(f"\nFunctions found: {len(functions)}")
    for func in functions[:15]:
        print(f"  - {func}")
    
    # Specifically check for download_page
    if hasattr(dv_module, 'download_page'):
        print("\n✓ download_page IS in the module")
        print(f"  Type: {type(dv_module.download_page)}")
    else:
        print("\n✗ download_page NOT in the module")
        
        # Check if it's defined but not accessible
        import inspect
        source_file = inspect.getfile(dv_module)
        print(f"\nChecking source file: {source_file}")
        
        # Try to read the file and see if download_page is there
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'def download_page' in content:
                print("  ✓ 'def download_page' found in source file")
                # Find the line number
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if 'def download_page' in line:
                        print(f"    Found at line {i}: {line.strip()}")
            else:
                print("  ✗ 'def download_page' NOT found in source file")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Testing via __init__.py ===")
try:
    from main.views import download_page
    print("✓ download_page imported via main.views")
except ImportError as e:
    print(f"✗ ImportError: {e}")
    # Check what's actually in main.views
    import main.views as views_module
    if hasattr(views_module, 'download_page'):
        print("  But download_page IS in main.views namespace")
    else:
        print("  And download_page is NOT in main.views namespace")
        # List some attributes
        attrs = [a for a in dir(views_module) if not a.startswith('_')][:10]
        print(f"  Sample attributes: {attrs}")

