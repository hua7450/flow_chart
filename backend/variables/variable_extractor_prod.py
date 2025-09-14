#!/usr/bin/env python3
"""
Variable extraction module for PolicyEngine variables - Production version.
Uses installed policyengine_us package instead of local files.
"""

import ast
import yaml
import inspect
import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Set, Optional, Any


class VariableExtractor:
    """Extracts PolicyEngine variables from installed package."""
    
    def __init__(self, base_path: str = None):
        # In production, we'll use the installed package
        self.use_installed_package = True
        self.base_path = Path(base_path) if base_path else None
        
        # Try local path first, fall back to installed package
        if self.base_path and self.base_path.exists():
            self.use_installed_package = False
        
    def load_all_variables(self) -> Dict[str, Dict]:
        """Load all variables from PolicyEngine package."""
        variables = {}
        
        if not self.use_installed_package and self.base_path:
            # Use local files (development mode)
            return self._load_from_local_files()
        
        # Use installed package (production mode)
        try:
            import policyengine_us.variables as peus_vars
            
            # Get all variable modules
            for importer, modname, ispkg in pkgutil.walk_packages(
                path=peus_vars.__path__,
                prefix=peus_vars.__name__ + '.',
                onerror=lambda x: None
            ):
                if ispkg:
                    continue
                    
                try:
                    module = importlib.import_module(modname)
                    
                    # Extract variable name from module
                    var_name = modname.split('.')[-1]
                    
                    # Look for variable class
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            hasattr(obj, 'value_type') and 
                            not name.startswith('_')):
                            
                            variable_data = self._extract_from_class(obj, var_name)
                            if variable_data:
                                variables[var_name] = variable_data
                                break
                                
                except Exception as e:
                    continue
                    
            print(f"Loaded {len(variables)} variables from installed policyengine-us package")
            
        except ImportError as e:
            print(f"Could not import policyengine_us: {e}")
            print("Please ensure policyengine-us is installed: pip install policyengine-us")
            
        return variables
    
    def _load_from_local_files(self) -> Dict[str, Dict]:
        """Load variables from local source files (original method)."""
        variables = {}
        
        if not self.base_path.exists():
            print(f"Path not found: {self.base_path}")
            return variables
        
        # Recursively find all Python files
        python_files = list(self.base_path.rglob("*.py"))
        
        for file_path in python_files:
            if "__pycache__" in str(file_path):
                continue
            
            variable_name = file_path.stem
            variable_data = self._extract_from_file(file_path, variable_name)
            
            if variable_data:
                variables[variable_name] = variable_data
        
        return variables
    
    def _extract_from_class(self, cls, var_name: str) -> Optional[Dict]:
        """Extract variable metadata from a class object."""
        try:
            data = {
                'name': var_name,
                'label': getattr(cls, 'label', var_name),
                'unit': getattr(cls, 'unit', None),
                'entity': getattr(cls, 'entity', None),
                'definition_period': getattr(cls, 'definition_period', None),
                'value_type': getattr(cls, 'value_type', None).__name__ if hasattr(cls, 'value_type') else None,
                'reference': getattr(cls, 'reference', None),
                'documentation': getattr(cls, 'documentation', cls.__doc__),
                'formulas': {},
                'parameters': set(),
                'variables': set(),
                'adds': [],
                'subtracts': []
            }
            
            # Extract formula information if available
            if hasattr(cls, 'formula'):
                # Get the source code of the formula method
                import inspect
                source = inspect.getsource(cls.formula)
                
                # Parse for parameters and variables (simplified)
                if 'parameters(' in source:
                    import re
                    params = re.findall(r'parameters\(["\']([^"\']+)["\']', source)
                    data['parameters'] = set(params)
                
                if '(period)' in source:
                    import re
                    vars = re.findall(r'([a-z_]+)\[period\]', source)
                    data['variables'] = set(vars)
            
            return data
            
        except Exception as e:
            return None
    
    def _extract_from_file(self, file_path: Path, variable_name: str) -> Optional[Dict]:
        """Extract variable metadata from a Python file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    data = {
                        'name': variable_name,
                        'file_path': str(file_path),
                        'label': None,
                        'unit': None,
                        'entity': None,
                        'definition_period': None,
                        'value_type': None,
                        'reference': None,
                        'documentation': ast.get_docstring(node),
                        'formulas': {},
                        'parameters': set(),
                        'variables': set(),
                        'adds': [],
                        'subtracts': []
                    }
                    
                    # Extract class attributes
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    attr_name = target.id
                                    if attr_name in ['label', 'unit', 'entity', 'definition_period', 'reference']:
                                        data[attr_name] = self._get_value(item.value)
                                    elif attr_name == 'value_type':
                                        data['value_type'] = self._get_value_type(item.value)
                        
                        elif isinstance(item, ast.FunctionDef) and item.name == 'formula':
                            formula_info = self._extract_formula_info(item)
                            data.update(formula_info)
                    
                    return data
            
            return None
            
        except Exception as e:
            return None
    
    def _get_value(self, node) -> Any:
        """Extract value from an AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_value(node.value)}.{node.attr}"
        return None
    
    def _get_value_type(self, node) -> str:
        """Extract value type from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return "unknown"
    
    def _extract_formula_info(self, func_node: ast.FunctionDef) -> Dict:
        """Extract information from a formula function."""
        info = {
            'parameters': set(),
            'variables': set(),
            'adds': [],
            'subtracts': []
        }
        
        for node in ast.walk(func_node):
            # Look for parameters
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'parameters' and node.args:
                        param = self._get_value(node.args[0])
                        if param:
                            info['parameters'].add(param)
            
            # Look for variable references
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Attribute):
                        var_name = self._get_value(node.value.args[0]) if node.value.args else None
                        if var_name:
                            info['variables'].add(var_name)
            
            # Look for add/subtract operations
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id == 'add':
                        for arg in node.args:
                            var = self._get_value(arg)
                            if var:
                                info['adds'].append(var)
                    elif node.func.id == 'subtract':
                        for arg in node.args:
                            var = self._get_value(arg)
                            if var:
                                info['subtracts'].append(var)
        
        return info