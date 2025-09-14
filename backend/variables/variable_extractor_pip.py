#!/usr/bin/env python3
"""
Variable extraction from installed policyengine-us package.
This version uses the pip-installed package instead of local files.
"""

import ast
import yaml
import inspect
import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import sys


class VariableExtractorPip:
    """Extracts PolicyEngine variables from installed pip package."""
    
    def __init__(self):
        # We'll use the installed policyengine_us package
        self.use_installed_package = True
        
    def load_all_variables(self) -> Dict[str, Dict]:
        """Load all variables from installed PolicyEngine package."""
        variables = {}
        
        try:
            # Import the installed policyengine_us package
            import policyengine_us
            import policyengine_us.variables as pe_variables
            
            print(f"Using policyengine-us version: {policyengine_us.__version__}")
            
            # Walk through all variable modules
            for importer, modname, ispkg in pkgutil.walk_packages(
                path=pe_variables.__path__,
                prefix=pe_variables.__name__ + '.',
                onerror=lambda x: None
            ):
                if ispkg:
                    continue
                    
                try:
                    # Import the module
                    module = importlib.import_module(modname)
                    
                    # Extract variable name from module path
                    var_name = modname.split('.')[-1]
                    
                    # Look for variable classes in the module
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            hasattr(obj, 'value_type') and 
                            not name.startswith('_')):
                            
                            # Extract metadata from the class
                            variable_data = self._extract_from_class(obj, var_name, module)
                            if variable_data:
                                variables[var_name] = variable_data
                                break
                                
                except Exception as e:
                    # Skip modules that can't be imported
                    continue
                    
            print(f"Loaded {len(variables)} variables from policyengine-us package")
            
        except ImportError as e:
            print(f"Error: Could not import policyengine_us: {e}")
            print("Please ensure policyengine-us is installed: pip install policyengine-us")
            
        return variables
    
    def _extract_from_class(self, cls, var_name: str, module) -> Optional[Dict]:
        """Extract variable metadata from a class object."""
        try:
            # Get the formula source if available
            formula_info = self._extract_formula_info(cls)
            
            data = {
                'name': var_name,
                'module_path': module.__name__,
                'label': getattr(cls, 'label', var_name),
                'unit': getattr(cls, 'unit', None),
                'entity': str(getattr(cls, 'entity', None)) if hasattr(cls, 'entity') else None,
                'definition_period': str(getattr(cls, 'definition_period', None)) if hasattr(cls, 'definition_period') else None,
                'value_type': getattr(cls, 'value_type', None).__name__ if hasattr(cls, 'value_type') else None,
                'reference': getattr(cls, 'reference', None),
                'documentation': getattr(cls, 'documentation', cls.__doc__),
                'parameters': formula_info.get('parameters', []),
                'variables': formula_info.get('variables', []),
                'adds': formula_info.get('adds', []),
                'subtracts': formula_info.get('subtracts', []),
                'defined_for': formula_info.get('defined_for', []),
                'possible_values': None,
                'enum_options': []
            }
            
            # Handle enum types
            if hasattr(cls, 'possible_values'):
                enum_cls = cls.possible_values
                if enum_cls:
                    data['possible_values'] = [item.name for item in enum_cls]
                    data['enum_options'] = [
                        {'name': item.name, 'value': item.value} 
                        for item in enum_cls
                    ]
            
            return data
            
        except Exception as e:
            return None
    
    def _extract_formula_info(self, cls) -> Dict:
        """Extract information from the formula method if it exists."""
        info = {
            'parameters': [],
            'variables': [],
            'adds': [],
            'subtracts': [],
            'defined_for': []
        }
        
        if not hasattr(cls, 'formula'):
            return info
            
        try:
            import inspect
            import re
            
            # Get the source code of the formula
            source = inspect.getsource(cls.formula)
            
            # Extract parameters using regex
            param_pattern = r'parameters\(["\']([^"\']+)["\']'
            params = re.findall(param_pattern, source)
            info['parameters'] = list(set(params))
            
            # Extract variable references
            # Look for patterns like: person("variable_name", period)
            var_pattern = r'(?:person|tax_unit|household|family|spm_unit)\(["\']([^"\']+)["\']'
            variables = re.findall(var_pattern, source)
            info['variables'] = list(set(variables))
            
            # Look for add() operations
            add_pattern = r'add\(\s*(?:person|tax_unit|household|family|spm_unit),["\']([^"\']+)["\']'
            adds = re.findall(add_pattern, source)
            info['adds'] = list(set(adds))
            
            # Look for defined_for conditions
            defined_pattern = r'defined_for\s*=\s*["\']([^"\']+)["\']'
            defined = re.findall(defined_pattern, source)
            info['defined_for'] = list(set(defined))
            
        except Exception as e:
            # If we can't get source, that's okay
            pass
            
        return info