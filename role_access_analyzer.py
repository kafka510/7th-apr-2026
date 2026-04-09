"""
Role Access Control Analyzer
----------------------------
Analyzes all views (function-based and class-based) to identify their role access requirements.

Usage:
    python role_access_analyzer.py [--output OUTPUT_FILE] [--filter FILTER]

Options:
    --output OUTPUT_FILE    Output CSV file (default: role_access_report.csv)
    --filter FILTER         Filter by access level (PUBLIC, LOGIN_REQUIRED, ROLE_BASED, SUPERUSER_ONLY, etc.)
"""

import os
import re
import ast
import csv
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

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

# Define the base directory
BASE_DIR = Path(__file__).parent

def discover_views_directories():
    """Auto-discover views files and directories in Django apps"""
    views_dirs = []
    seen_paths = set()
    
    # Find all views.py files
    for views_path in BASE_DIR.rglob('views.py'):
        # Skip venv, migrations, and Django internal files
        path_str = str(views_path)
        if any(x in path_str for x in ['venv', '__pycache__', 'migrations', 'site-packages', '.git']):
            continue
        
        views_dir = views_path.parent
        rel_path = str(views_dir.relative_to(BASE_DIR))
        if rel_path not in seen_paths:
            views_dirs.append(views_dir)
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
            views_dirs.append(views_dir)
            seen_paths.add(rel_path)
    
    return views_dirs

# Auto-discover views directories (with fallback to manual list)
try:
    VIEWS_DIRS = discover_views_directories()
    AUTO_DISCOVERY_ENABLED = True
except Exception as e:
    # Fallback to manual list if auto-discovery fails
    print(f"⚠️  Auto-discovery failed: {e}. Using manual list.")
    VIEWS_DIRS = [
        BASE_DIR / 'main' / 'views',
        BASE_DIR / 'accounts',
        BASE_DIR / 'api',
        BASE_DIR / 'ticketing' / 'views',
    ]
    AUTO_DISCOVERY_ENABLED = False

# Role definitions
ROLE_LEVELS = {
    'PUBLIC': 0,
    'LOGIN_REQUIRED': 1,
    'API_AUTH': 2,
    'FEATURE_BASED': 3,
    'CAPABILITY_BASED': 4,
    'ROLE_BASED': 5,
    'ADMIN_OR_SUPERUSER': 6,
    'SUPERUSER_ONLY': 7,
}

# Common admin roles
ADMIN_ROLES = ['admin', 'superuser', 'manager']
SUPERUSER_ROLES = ['superuser']


def resolve_variable_value(var_name: str, file_path: Path) -> Optional[List[str]]:
    """Try to resolve a variable's value from the file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return None
    
    # Common role constants to look for
    known_constants = {
        'USER_MANAGEMENT_MANAGER_ROLES': ['admin'],  # Default fallback
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    # Try to extract the value
                    if isinstance(node.value, ast.List):
                        roles = []
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant):
                                roles.append(elt.value)
                            elif isinstance(elt, ast.Str):
                                roles.append(elt.s)
                        if roles:
                            return roles
                    elif isinstance(node.value, ast.IfExp):
                        # Handle: _roles if _roles else ['admin']
                        if isinstance(node.value.body, ast.List):
                            roles = []
                            for elt in node.value.body.elts:
                                if isinstance(elt, ast.Constant):
                                    roles.append(elt.value)
                                elif isinstance(elt, ast.Str):
                                    roles.append(elt.s)
                            if roles:
                                return roles
    
    # Return known constant if found
    return known_constants.get(var_name)


def parse_role_required_decorator(decorator_node, file_path: Path) -> Optional[List[str]]:
    """Extract roles from @role_required decorator"""
    if isinstance(decorator_node, ast.Call):
        func = decorator_node.func
        if isinstance(func, ast.Name) and func.id == 'role_required':
            # Check for allowed_roles argument
            for keyword in decorator_node.keywords:
                if keyword.arg == 'allowed_roles':
                    if isinstance(keyword.value, ast.List):
                        roles = []
                        for elt in keyword.value.elts:
                            if isinstance(elt, ast.Constant):
                                roles.append(elt.value)
                            elif isinstance(elt, ast.Str):  # Python < 3.8
                                roles.append(elt.s)
                        return roles
                    elif isinstance(keyword.value, ast.Name):
                        # Variable reference - try to resolve it
                        var_name = keyword.value.id
                        resolved = resolve_variable_value(var_name, file_path)
                        if resolved:
                            return resolved
                        return ['<variable>']
            # Default empty list
            return []
    return None


def find_test_function_definition(func_name: str, file_path: Path) -> Optional[str]:
    """Find and analyze a test function definition"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return None
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            # Check if it checks is_superuser
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Attribute):
                    if isinstance(stmt.value, ast.Name) and stmt.value.id in ['user', 'u']:
                        if stmt.attr == 'is_superuser':
                            return 'SUPERUSER_ONLY'
                # Check for user_has_capability calls
                if isinstance(stmt, ast.Call):
                    func = stmt.func
                    if isinstance(func, ast.Name) and func.id == 'user_has_capability':
                        return 'ADMIN_OR_SUPERUSER'
                    elif isinstance(func, ast.Attribute) and func.attr == 'user_has_capability':
                        return 'ADMIN_OR_SUPERUSER'
    
    return None


def parse_user_passes_test(decorator_node, file_path: Path) -> Optional[str]:
    """Extract test function from @user_passes_test decorator"""
    if isinstance(decorator_node, ast.Call):
        func = decorator_node.func
        if isinstance(func, ast.Name) and func.id == 'user_passes_test':
            if decorator_node.args:
                arg = decorator_node.args[0]
                # Lambda: lambda u: u.is_superuser
                if isinstance(arg, ast.Lambda):
                    body = arg.body
                    if isinstance(body, ast.Attribute):
                        if isinstance(body.value, ast.Name) and body.value.id == 'u':
                            if body.attr == 'is_superuser':
                                return 'SUPERUSER_ONLY'
                            elif body.attr == 'is_staff':
                                return 'STAFF_ONLY'
                    # Check for OR conditions: u.is_superuser or user_has_capability(...)
                    elif isinstance(body, ast.BoolOp) and isinstance(body.op, ast.Or):
                        return 'ADMIN_OR_SUPERUSER'
                # Function reference: is_admin
                elif isinstance(arg, ast.Name):
                    test_result = find_test_function_definition(arg.id, file_path)
                    if test_result:
                        return test_result
                    return f'CUSTOM_TEST:{arg.id}'
    return None


def parse_superuser_required(decorator_node) -> bool:
    """Check if decorator is @superuser_required"""
    if isinstance(decorator_node, ast.Name):
        return decorator_node.id == 'superuser_required'
    elif isinstance(decorator_node, ast.Call):
        func = decorator_node.func
        if isinstance(func, ast.Name):
            return func.id == 'superuser_required'
    return False


def analyze_function_decorators(func_node, file_path: Path) -> Dict:
    """Analyze decorators on a function-based view"""
    access_info = {
        'access_level': 'PUBLIC',
        'roles': [],
        'decorators': [],
        'details': [],
        'has_superuser': False,
        'has_api_auth': False
    }
    
    decorators = []
    file_path_obj = Path(file_path) if isinstance(file_path, str) else file_path
    
    for decorator in func_node.decorator_list:
        decorator_str = ast.unparse(decorator) if hasattr(ast, 'unparse') else str(decorator)
        decorators.append(decorator_str)
        
        # Check for require_api_auth (API authentication)
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == 'require_api_auth':
                access_info['has_api_auth'] = True
                if access_info['access_level'] == 'PUBLIC':
                    access_info['access_level'] = 'API_AUTH'
                    access_info['details'].append('API authentication required')
        
        # Check for login_required
        if isinstance(decorator, ast.Name) and decorator.id == 'login_required':
            if access_info['access_level'] == 'PUBLIC':
                access_info['access_level'] = 'LOGIN_REQUIRED'
        
        # Check for superuser_required (highest priority)
        elif parse_superuser_required(decorator):
            access_info['has_superuser'] = True
            access_info['access_level'] = 'SUPERUSER_ONLY'
            access_info['details'].append('Superuser only')
        
        # Check for user_passes_test
        elif isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == 'user_passes_test':
                test_result = parse_user_passes_test(decorator, file_path_obj)
                if test_result == 'SUPERUSER_ONLY':
                    access_info['has_superuser'] = True
                    access_info['access_level'] = 'SUPERUSER_ONLY'
                    access_info['details'].append('user_passes_test(lambda u: u.is_superuser)')
                elif test_result == 'ADMIN_OR_SUPERUSER':
                    access_info['access_level'] = 'ADMIN_OR_SUPERUSER'
                    access_info['details'].append('user_passes_test (checks superuser or capability)')
                elif test_result and test_result.startswith('CUSTOM_TEST:'):
                    access_info['access_level'] = 'ADMIN_OR_SUPERUSER'
                    access_info['details'].append(f'user_passes_test({test_result.split(":")[1]})')
            
            # Check for role_required
            elif isinstance(func, ast.Name) and func.id == 'role_required':
                roles = parse_role_required_decorator(decorator, file_path_obj)
                if roles and '<variable>' not in roles:
                    # Only set ROLE_BASED if not already SUPERUSER_ONLY
                    if access_info['access_level'] != 'SUPERUSER_ONLY':
                        access_info['access_level'] = 'ROLE_BASED'
                    access_info['roles'] = roles
                    if access_info['has_superuser']:
                        access_info['details'].append(f'role_required({roles}) - redundant (superuser already required)')
                    else:
                        access_info['details'].append(f'role_required({roles})')
                elif roles:
                    # Variable roles - try to resolve
                    access_info['roles'] = roles
                    if access_info['access_level'] != 'SUPERUSER_ONLY':
                        access_info['access_level'] = 'ROLE_BASED'
            
            # Check for feature_required
            elif isinstance(func, ast.Name) and func.id == 'feature_required':
                if decorator.args:
                    feature = decorator.args[0]
                    if isinstance(feature, ast.Constant):
                        feature_name = feature.value
                    elif isinstance(feature, ast.Str):
                        feature_name = feature.s
                    else:
                        feature_name = '<variable>'
                    if access_info['access_level'] != 'SUPERUSER_ONLY':
                        access_info['access_level'] = 'FEATURE_BASED'
                    access_info['details'].append(f'feature_required({feature_name})')
    
    access_info['decorators'] = decorators
    return access_info


def analyze_class_mixins(class_node, file_path: Path) -> Dict:
    """Analyze mixins and base classes for role access"""
    access_info = {
        'access_level': 'PUBLIC',
        'roles': [],
        'mixins': [],
        'details': [],
        'has_superuser': False
    }
    file_path_obj = Path(file_path) if isinstance(file_path, str) else file_path
    
    # Check base classes
    for base in class_node.bases:
        base_name = None
        if isinstance(base, ast.Name):
            base_name = base.id
        elif isinstance(base, ast.Attribute):
            base_name = base.attr
        
        if base_name:
            access_info['mixins'].append(base_name)
            
            # Check for security mixins
            if 'LoginRequiredMixin' in base_name:
                if access_info['access_level'] == 'PUBLIC':
                    access_info['access_level'] = 'LOGIN_REQUIRED'
            
            if 'AccessControlMixin' in base_name:
                access_info['access_level'] = 'CAPABILITY_BASED'
                access_info['details'].append('AccessControlMixin (checks capability: accounts.manage_access)')
            
            if 'UserPassesTestMixin' in base_name:
                access_info['access_level'] = 'ADMIN_OR_SUPERUSER'
                access_info['details'].append('UserPassesTestMixin (checks superuser or capability)')
    
    # Check class decorators
    for decorator in class_node.decorator_list:
        decorator_str = ast.unparse(decorator) if hasattr(ast, 'unparse') else str(decorator)
        
        # Check for method_decorator(login_required)
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == 'method_decorator':
                if decorator.args:
                    arg = decorator.args[0]
                    if isinstance(arg, ast.Name) and arg.id == 'login_required':
                        if access_info['access_level'] == 'PUBLIC':
                            access_info['access_level'] = 'LOGIN_REQUIRED'
                        access_info['details'].append('@method_decorator(login_required)')
    
    return access_info


def analyze_view_file(file_path: Path) -> List[Dict]:
    """Analyze a Python file for views and their access control"""
    results = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        print(f"⚠️  Error parsing {file_path}: {e}")
        return results
    
    # Helper function to check if a function/class is likely a view
    def is_likely_view(node_name: str, file_path: Path, node_type: str) -> bool:
        """Check if a function/class is likely a Django view"""
        path_str = str(file_path).lower()
        
        # Skip if it's in certain directories/files
        exclude_patterns = [
            'migrations', '__pycache__', 'management/commands', 
            'admin.py', 'models.py', 'forms.py', 'apps.py', 'backends.py', 
            'decorators.py', 'middleware', 'validators.py', 'permissions.py', 
            'filtering.py', 'authentication.py', 'brute_force_protection.py',
            'tasks.py', 'utils.py', 'shared/utilities.py', 'shared/validators.py',
            'shared/permissions.py'
        ]
        if any(x in path_str for x in exclude_patterns):
            return False
        
        # Skip Celery tasks (will be checked in caller)
        if 'tasks.py' in path_str:
            return False
        
        # Skip common non-view names (helper functions)
        non_view_names = {
            'safe_val', 'clean', 'save', 'delete', 'get_queryset', 'get_context_data',
            'form_valid', 'form_invalid', 'dispatch', 'get', 'post', 'put', 'patch',
            'head', 'options', 'trace', 'authenticate', 'get_user', 'check_password',
            'set_password', 'has_perm', 'has_module_perms', 'is_anonymous', 'is_authenticated',
            'add_arguments', 'handle', 'cleanup', 'check', 'apply', 'calculate', 'parse',
            'validate', 'format', 'convert', 'extract', 'generate', 'create', 'update',
            'delete', 'list', 'get_object', 'get_form', 'get_form_class', 'get_success_url',
            'add_success_message', 'get_cancel_url', 'invalidate_permissions',
            'test_func', 'handle_no_permission', 'wrapper',
            # Helper function patterns
            'can_', 'has_', 'is_', 'get_', 'check_', 'find_', 'parse_', 'calculate_',
            'create_', 'update_', 'delete_', 'send_', 'log_', 'export_', 'import_',
            'filter_', 'process_', 'detect_', 'ensure_', 'coerce_', 'make_',
        }
        if any(node_name.lower().startswith(prefix) for prefix in ['can_', 'has_', 'is_', 'get_', 'check_', 'find_', 'parse_', 'calculate_', 'create_', 'update_', 'delete_', 'send_', 'log_', 'export_', 'import_', 'filter_', 'process_', 'detect_', 'ensure_', 'coerce_', 'make_']):
            # But allow if it's clearly a view (has request param - checked later)
            pass
        elif node_name.lower() in non_view_names:
            return False
        
        # Skip if it's a model, form, admin, or command class
        if node_name.endswith(('Model', 'Form', 'Admin', 'Config', 'Backend', 'Middleware', 'Exception', 'Error', 'Command')):
            return False
        
        # Skip pure mixins (unless they're used as views)
        if node_type == 'class' and node_name.endswith('Mixin') and 'View' not in node_name:
            return False
        
        # For classes, check if they inherit from Django View classes
        if node_type == 'class':
            # Must have View in name OR inherit from View classes
            if 'View' in node_name:
                return True
            # Skip if it's clearly not a view
            if any(x in node_name for x in ['Model', 'Form', 'Admin', 'Config', 'Backend', 'Middleware', 'Command', 'Task']):
                return False
        
        # For functions, we'll check for request parameter in caller
        return True
    
    # Track seen views to avoid duplicates
    seen_views = set()
    
    for node in ast.walk(tree):
        # Function-based views
        if isinstance(node, ast.FunctionDef):
            # Skip private functions
            if node.name.startswith('_'):
                continue
            
            # Skip decorator definitions and wrapper functions
            if node.name in ['superuser_required', 'role_required', 'feature_required', 'wrapper']:
                continue
            
            # Check if function takes 'request' parameter (Django view signature)
            has_request_param = False
            if node.args.args:
                first_param = node.args.args[0]
                if isinstance(first_param, ast.arg) and first_param.arg == 'request':
                    has_request_param = True
            
            # Skip if no request parameter - must have request to be a view
            if not has_request_param:
                continue
            
            # Skip helper functions in non-view files (even if they have request)
            path_str = str(file_path).lower()
            helper_file_patterns = ['decorators.py', 'authentication.py', 'utils.py', 'permissions.py', 'validators.py', 'filtering.py']
            if any(x in path_str for x in helper_file_patterns):
                # Skip helper functions (get_*, check_*, can_*, has_*, is_*, extract_*, log_*)
                helper_prefixes = ['get_', 'check_', 'can_', 'has_', 'is_', 'extract_', 'log_', 'find_', 'parse_', 'calculate_']
                if any(node.name.lower().startswith(prefix) for prefix in helper_prefixes):
                    continue
            
            # Skip Celery tasks
            has_shared_task = any(
                isinstance(d, ast.Call) and 
                isinstance(d.func, ast.Name) and 
                d.func.id == 'shared_task'
                for d in node.decorator_list
            )
            if has_shared_task:
                continue
            
            # Create unique identifier to avoid duplicates
            view_id = (node.name, str(file_path), node.lineno)
            if view_id in seen_views:
                continue
            seen_views.add(view_id)
            
            access_info = analyze_function_decorators(node, file_path)
            
            results.append({
                'name': node.name,
                'type': 'function',
                'file': str(file_path.relative_to(BASE_DIR)),
                'line': node.lineno,
                'access_level': access_info['access_level'],
                'roles': ', '.join(access_info['roles']) if access_info['roles'] else '',
                'decorators': '; '.join(access_info['decorators']),
                'details': '; '.join(access_info['details']) if access_info['details'] else '',
            })
        
        # Class-based views
        elif isinstance(node, ast.ClassDef):
            # Skip private classes
            if node.name.startswith('_'):
                continue
            
            # Skip pure mixins (unless they're used as views)
            if node.name.endswith('Mixin') and 'View' not in node.name:
                # Check if it inherits from View classes
                inherits_from_view = False
                for base in node.bases:
                    base_name = None
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    if base_name and 'View' in base_name:
                        inherits_from_view = True
                        break
                if not inherits_from_view:
                    continue
            
            # Skip management command classes
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == 'BaseCommand':
                    continue
            
            # Skip MockRequest and Meta classes
            if node.name in ['MockRequest', 'Meta']:
                continue
            
            # Skip classes with Mock in name
            if 'Mock' in node.name:
                continue
            
            # Only include if it's likely a view class
            if not is_likely_view(node.name, file_path, 'class'):
                continue
            
            # Create unique identifier to avoid duplicates
            view_id = (node.name, str(file_path), node.lineno)
            if view_id in seen_views:
                continue
            seen_views.add(view_id)
            
            access_info = analyze_class_mixins(node, file_path)
            
            # Check for dispatch method decorators
            has_superuser_in_methods = False
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == 'dispatch':
                    func_access = analyze_function_decorators(item, file_path)
                    if func_access['access_level'] != 'PUBLIC':
                        # Apply superuser precedence - superuser overrides everything
                        if func_access.get('has_superuser'):
                            access_info['access_level'] = 'SUPERUSER_ONLY'
                            access_info['has_superuser'] = True
                            access_info['details'].append('Superuser required (from method decorator)')
                        elif access_info['access_level'] != 'SUPERUSER_ONLY':
                            access_info['access_level'] = func_access['access_level']
                        access_info['details'].extend([d for d in func_access['details'] if d not in access_info['details']])
                    if func_access.get('has_superuser'):
                        has_superuser_in_methods = True
            
            # Final superuser precedence check
            if (access_info.get('has_superuser') or has_superuser_in_methods) and access_info['access_level'] != 'SUPERUSER_ONLY':
                access_info['access_level'] = 'SUPERUSER_ONLY'
                if not any('Superuser' in d for d in access_info['details']):
                    access_info['details'].append('Superuser required')
            
            results.append({
                'name': node.name,
                'type': 'class',
                'file': str(file_path.relative_to(BASE_DIR)),
                'line': node.lineno,
                'access_level': access_info['access_level'],
                'roles': ', '.join(access_info['roles']) if access_info['roles'] else '',
                'decorators': '; '.join(access_info['mixins']) if access_info['mixins'] else '',
                'details': '; '.join(access_info['details']) if access_info['details'] else '',
            })
    
    return results


def find_all_view_files() -> List[Path]:
    """Find all Python files in view directories"""
    view_files = []
    
    for views_dir in VIEWS_DIRS:
        if not views_dir.exists():
            continue
        
        for py_file in views_dir.rglob('*.py'):
            # Skip __pycache__ and migrations
            if '__pycache__' in str(py_file) or 'migrations' in str(py_file):
                continue
            view_files.append(py_file)
    
    return view_files


def categorize_by_access_level(results: List[Dict]) -> Dict[str, List[Dict]]:
    """Group results by access level"""
    categorized = defaultdict(list)
    
    for result in results:
        level = result['access_level']
        categorized[level].append(result)
    
    return dict(categorized)


def generate_report(results: List[Dict], output_file: str = 'role_access_report.csv'):
    """Generate CSV report"""
    # Sort by access level priority, then by name
    def sort_key(r):
        level_priority = ROLE_LEVELS.get(r['access_level'], 999)
        return (level_priority, r['name'].lower())
    
    sorted_results = sorted(results, key=sort_key)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'View Name', 'Type', 'Access Level', 'Roles', 'File', 'Line', 'Decorators/Mixins', 'Details'
        ])
        writer.writeheader()
        
        for result in sorted_results:
            writer.writerow({
                'View Name': result['name'],
                'Type': result['type'],
                'Access Level': result['access_level'],
                'Roles': result['roles'],
                'File': result['file'],
                'Line': result['line'],
                'Decorators/Mixins': result['decorators'],
                'Details': result['details'],
            })
    
    print(f"✅ Report saved to: {output_file}")


def print_summary(categorized: Dict[str, List[Dict]]):
    """Print summary statistics"""
    print(f"\n{'='*80}")
    print(f"📊 ROLE ACCESS ANALYSIS SUMMARY")
    print(f"{'='*80}\n")
    
    total = sum(len(views) for views in categorized.values())
    
    level_order = ['PUBLIC', 'LOGIN_REQUIRED', 'API_AUTH', 'FEATURE_BASED', 'CAPABILITY_BASED', 
                   'ROLE_BASED', 'ADMIN_OR_SUPERUSER', 'SUPERUSER_ONLY']
    
    for level in level_order:
        if level in categorized:
            views = categorized[level]
            count = len(views)
            percentage = (count / total * 100) if total > 0 else 0
            
            icon = '🔓' if level == 'PUBLIC' else '🔐' if 'SUPERUSER' in level else '🔑'
            
            print(f"{icon} {level:25} {count:4} views ({percentage:5.1f}%)")
    
    print(f"\n{'='*80}")
    print(f"Total Views Analyzed: {total}")
    print(f"{'='*80}\n")


def print_detailed_report(categorized: Dict[str, List[Dict]], filter_level: Optional[str] = None):
    """Print detailed report by access level"""
    level_order = ['SUPERUSER_ONLY', 'ADMIN_OR_SUPERUSER', 'ROLE_BASED', 
                   'CAPABILITY_BASED', 'FEATURE_BASED', 'API_AUTH', 'LOGIN_REQUIRED', 'PUBLIC']
    
    for level in level_order:
        if level not in categorized:
            continue
        
        if filter_level and level != filter_level:
            continue
        
        views = categorized[level]
        if not views:
            continue
        
        print(f"\n{'='*80}")
        print(f"🔍 {level} ({len(views)} views)")
        print(f"{'='*80}\n")
        
        # Sort by name
        sorted_views = sorted(views, key=lambda x: x['name'].lower())
        
        for view in sorted_views[:50]:  # Limit to first 50
            print(f"  • {view['name']:40} ({view['type']:8}) | {view['file']}:{view['line']}")
            if view['roles']:
                print(f"    Roles: {view['roles']}")
            if view['details']:
                print(f"    Details: {view['details']}")
        
        if len(sorted_views) > 50:
            print(f"\n  ... and {len(sorted_views) - 50} more")


def main():
    parser = argparse.ArgumentParser(description='Analyze role-based access control in Django views')
    parser.add_argument('--output', default='role_access_report.csv', 
                       help='Output CSV file (default: role_access_report.csv)')
    parser.add_argument('--filter', choices=['PUBLIC', 'LOGIN_REQUIRED', 'API_AUTH', 'ROLE_BASED', 
                                            'SUPERUSER_ONLY', 'ADMIN_OR_SUPERUSER', 
                                            'FEATURE_BASED', 'CAPABILITY_BASED'],
                       help='Filter by access level')
    parser.add_argument('--summary-only', action='store_true',
                       help='Only show summary, skip detailed report')
    
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print(f"🔐 Role Access Control Analyzer")
    print(f"{'='*80}\n")
    if AUTO_DISCOVERY_ENABLED:
        print(f"✅ Auto-Discovery: Enabled (found {len(VIEWS_DIRS)} view locations)")
    else:
        print(f"⚠️  Auto-Discovery: Disabled (using manual list)")
    print("Scanning view files...")
    
    # Find all view files
    view_files = find_all_view_files()
    print(f"Found {len(view_files)} Python files to analyze\n")
    
    # Analyze all files
    all_results = []
    for view_file in view_files:
        results = analyze_view_file(view_file)
        all_results.extend(results)
    
    # Categorize results
    categorized = categorize_by_access_level(all_results)
    
    # Print summary
    print_summary(categorized)
    
    # Generate CSV report
    generate_report(all_results, args.output)
    
    # Print detailed report
    if not args.summary_only:
        print_detailed_report(categorized, args.filter)
    
    # Highlight potential issues
    print(f"\n{'='*80}")
    print(f"⚠️  POTENTIAL SECURITY CONCERNS")
    print(f"{'='*80}\n")
    
    public_views = categorized.get('PUBLIC', [])
    if public_views:
        print(f"🔓 PUBLIC views found ({len(public_views)}):")
        for view in public_views[:10]:
            print(f"   - {view['name']} ({view['file']}:{view['line']})")
        if len(public_views) > 10:
            print(f"   ... and {len(public_views) - 10} more")
        print()
    
    # Check for views that should be superuser-only
    superuser_views = categorized.get('SUPERUSER_ONLY', [])
    admin_superuser_views = categorized.get('ADMIN_OR_SUPERUSER', [])
    
    print(f"✅ SUPERUSER_ONLY views: {len(superuser_views)}")
    print(f"✅ ADMIN_OR_SUPERUSER views: {len(admin_superuser_views)}")
    print(f"✅ Total restricted admin views: {len(superuser_views) + len(admin_superuser_views)}\n")
    
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()

