import sys
import importlib.util

# Load the module directly without Django
spec = importlib.util.spec_from_file_location('download_views', 'main/views/download_views.py')
module = importlib.util.module_from_spec(spec)

try:
    print("Attempting to load download_views.py directly...")
    spec.loader.exec_module(module)
    print("✓ Module loaded successfully")
    
    # Check for download_page
    if hasattr(module, 'download_page'):
        print("✓ download_page found!")
    else:
        print("✗ download_page NOT found")
    
    # List all callable attributes
    callables = [x for x in dir(module) if not x.startswith('_') and callable(getattr(module, x, None))]
    print(f"\nCallable functions/classes found: {len(callables)}")
    for name in callables[:10]:
        print(f"  - {name}")
        
except Exception as e:
    print(f"✗ Error loading module: {e}")
    import traceback
    traceback.print_exc()

