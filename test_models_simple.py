#!/usr/bin/env python
"""Simple test to verify models and plugin system"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')
django.setup()

print("Testing models import...")
from main.models import PVModuleDatasheet, PowerModelRegistry
print("✅ Models imported!")

print("\nTesting plugin system...")
try:
    from main.calculations.models import model_registry
    print("✅ model_registry imported!")
    
    models = model_registry.list_models()
    print(f"✅ Found {len(models)} registered models")
    
    for m in models:
        print(f"   - {m['name']} v{m['version']} (Code: {m['code']}, Default: {m['is_default']})")
    
    print("\n✅ ALL TESTS PASSED!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

