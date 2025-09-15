"""
UK Variable Extractor with dual approach:
1. Try local folder first (for development)
2. Fall back to pip package (for Railway deployment)
"""

import ast
import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Set, Optional
import logging

logger = logging.getLogger(__name__)

class UKVariableExtractor:
    """Extract UK variables from local folder or pip package"""
    
    def __init__(self, base_path: str = "../policyengine-uk/policyengine_uk/variables"):
        self.variables_cache = {}
        self.base_path = Path(base_path)
        self.package_name = 'policyengine_uk'
        
    def load_all_variables(self) -> Dict:
        """Load all UK variables from local folder or pip package"""
        # First try local folder (for development)
        if self.base_path.exists():
            print(f"Loading UK variables from local folder: {self.base_path}")
            return self._load_from_folder()
        
        # Fall back to pip package (for Railway)
        print("Local UK folder not found, trying pip package...")
        return self._load_from_package()
    
    def _load_from_folder(self) -> Dict:
        """Load variables from local PolicyEngine-UK folder"""
        variables = {}
        
        # Recursively find all Python files
        python_files = list(self.base_path.rglob("*.py"))
        
        for file_path in python_files:
            if "__pycache__" in str(file_path):
                continue
            
            variable_name = file_path.stem
            variable_data = self._extract_from_file(file_path, variable_name)
            
            if variable_data:
                variables[variable_name] = variable_data
        
        print(f"Loaded {len(variables)} UK variables from local folder")
        return variables
    
    def _load_from_package(self) -> Dict:
        """Load variables from installed pip package"""
        try:
            # Import the UK package
            uk_package = importlib.import_module(self.package_name)
            
            # Get the variables module
            variables_module = importlib.import_module(f'{self.package_name}.variables')
            
            # Walk through all submodules in variables
            variables_path = Path(variables_module.__file__).parent
            
            for root, dirs, files in variables_path.rglob('*.py'):
                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        self._process_file(Path(root) / file)
            
            logger.info(f"Loaded {len(self.variables_cache)} UK variables from pip package")
            return self.variables_cache
            
        except ImportError as e:
            logger.warning(f"PolicyEngine-UK package not installed: {e}")
            logger.info("UK support will be disabled. Install with: pip install PolicyEngine-UK")
            # Return empty cache - UK will be unavailable but US will still work
            return {}
    
    def _extract_from_file(self, file_path: Path, variable_name: str) -> Optional[Dict]:
        """Extract metadata from a variable file (for folder approach)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if this is a variable class
                    if self._is_variable_class(node):
                        metadata = self._extract_metadata(node, file_path)
                        if metadata:
                            return metadata
            
            return None
        except Exception as e:
            # Skip files that fail to parse
            return None
    
    def _process_file(self, file_path: Path):
        """Process a single Python file to extract variables (for package approach)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if this is a variable class
                    if self._is_variable_class(node):
                        var_name = self._extract_variable_name(node)
                        if var_name:
                            metadata = self._extract_metadata(node, file_path)
                            self.variables_cache[var_name] = metadata
                            
        except Exception as e:
            logger.debug(f"Error processing {file_path}: {e}")
    
    def _is_variable_class(self, node: ast.ClassDef) -> bool:
        """Check if a class is a variable definition"""
        # UK variables typically inherit from Variable or similar base classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                if 'variable' in base.id.lower():
                    return True
        return False
    
    def _extract_variable_name(self, node: ast.ClassDef) -> Optional[str]:
        """Extract variable name from class definition"""
        # First try to get from class name (snake_case version)
        var_name = self._camel_to_snake(node.name)
        
        # Look for explicit name attribute
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == 'name':
                        if isinstance(item.value, ast.Constant):
                            return item.value.value
        
        return var_name
    
    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _extract_metadata(self, node: ast.ClassDef, file_path: Path) -> Dict:
        """Extract metadata from variable class"""
        metadata = {
            'name': self._extract_variable_name(node),
            'file_path': str(file_path),
            'variables': set(),
            'parameters': {},  # Changed to dict for compatibility
            'adds': [],
            'subtracts': [],
            'label': None,
            'description': None,
            'entity': None,
            'value_type': None,
            'defined_for': None,
            'country': 'UK'  # Mark as UK variable
        }
        
        # Extract various metadata from class body
        for item in node.body:
            # Extract label
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if target.id == 'label':
                            metadata['label'] = self._extract_string_value(item.value)
                        elif target.id == 'documentation':
                            metadata['description'] = self._extract_string_value(item.value)
                        elif target.id == 'entity':
                            metadata['entity'] = self._extract_entity(item.value)
                        elif target.id == 'value_type':
                            metadata['value_type'] = self._extract_value_type(item.value)
                        elif target.id == 'defined_for':
                            metadata['defined_for'] = self._extract_string_value(item.value)
                        elif target.id == 'adds':
                            # Handle adds as a list
                            adds_list = self._extract_list_value(item.value)
                            if adds_list:
                                metadata['adds'] = adds_list
                        elif target.id == 'subtracts':
                            # Handle subtracts as a list
                            subtracts_list = self._extract_list_value(item.value)
                            if subtracts_list:
                                metadata['subtracts'] = subtracts_list
            
            # Extract formula dependencies
            elif isinstance(item, ast.FunctionDef) and item.name == 'formula':
                formula_vars, params, adds, subtracts = self._extract_formula_dependencies(item)
                metadata['variables'].update(formula_vars)
                # Parameters are now already a dict
                metadata['parameters'].update(params)
                metadata['adds'].extend(adds)
                metadata['subtracts'].extend(subtracts)
        
        # Convert sets to lists for JSON serialization
        metadata['variables'] = list(metadata['variables'])
        
        return metadata
    
    def _extract_string_value(self, node) -> Optional[str]:
        """Extract string value from AST node"""
        if isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Str):
            return node.s
        return None
    
    def _extract_list_value(self, node) -> Optional[List[str]]:
        """Extract list of strings from AST node"""
        if isinstance(node, ast.List):
            items = []
            for elt in node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    items.append(elt.value)
                elif isinstance(elt, ast.Str):
                    items.append(elt.s)
            return items if items else None
        return None
    
    def _extract_entity(self, node) -> Optional[str]:
        """Extract entity type"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return '.'.join(reversed(parts))
        return None
    
    def _extract_value_type(self, node) -> Optional[str]:
        """Extract value type"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
        return None
    
    def _extract_parameter_path(self, node: ast.Attribute) -> str:
        """Extract parameter path from attribute chain starting with parameters(period)."""
        path_parts = []
        current = node
        
        # Walk up the attribute chain
        while isinstance(current, ast.Attribute):
            path_parts.append(current.attr)
            current = current.value
        
        # Check if this chain starts with parameters(period)
        if isinstance(current, ast.Call):
            if (isinstance(current.func, ast.Name) and 
                current.func.id == 'parameters' and 
                len(current.args) >= 1):
                # This is a parameters(period) call, reverse the path and join
                path_parts.reverse()
                return '.'.join(path_parts) if path_parts else ''
        
        return ''
    
    def _extract_formula_dependencies(self, func_node: ast.FunctionDef) -> tuple:
        """Extract variable and parameter dependencies from formula"""
        variables = set()
        parameters = {}
        adds = []
        subtracts = []
        param_var_assignments = {}
        
        # First pass: identify parameter assignments like p = parameters(period).gov.dwp...
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Look for parameters(period) assignments
                        if isinstance(node.value, ast.Attribute):
                            param_path = self._extract_parameter_path(node.value)
                            if param_path:
                                # Store as both a parameter and track for sub-attribute access
                                parameters[target.id] = param_path
                                param_var_assignments[target.id] = param_path
                        elif isinstance(node.value, ast.Subscript):
                            # Handle subscripted parameters
                            if isinstance(node.value.value, ast.Attribute):
                                param_path = self._extract_parameter_path(node.value.value)
                                if param_path:
                                    param_name = param_path.split('.')[-1]
                                    parameters[param_name] = param_path
        
        # Second pass: find actual parameter usage (e.g., wfp.amount.higher)
        for node in ast.walk(func_node):
            if isinstance(node, ast.Attribute):
                # Check if this is a parameter usage like wfp.amount.higher
                # Build the full chain from this attribute node
                chain = []
                current = node
                while isinstance(current, ast.Attribute):
                    chain.append(current.attr)
                    current = current.value
                
                # Check if the base is a parameter variable (like 'wfp')
                if isinstance(current, ast.Name) and current.id in param_var_assignments:
                    chain.reverse()  # Now chain is ['amount', 'higher'] for wfp.amount.higher
                    base_path = param_var_assignments[current.id]
                    
                    # Combine base path with the attribute chain
                    full_param_path = base_path
                    for part in chain:
                        full_param_path = f"{full_param_path}.{part}"
                    
                    # Use the last part as the parameter name (e.g., 'higher')
                    param_name = chain[-1] if chain else node.attr
                    parameters[param_name] = full_param_path
        
        # Third pass: extract variables and other operations
        for node in ast.walk(func_node):
            # Look for variable references (e.g., household("variable_name", period))
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and len(node.args) >= 1:
                    if isinstance(node.args[0], ast.Constant):
                        var_name = node.args[0].value
                        if isinstance(var_name, str):
                            variables.add(var_name)
                
                # Look for add/subtract operations  
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'add' and len(node.args) >= 2:
                        for arg in node.args[1:]:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                adds.append(arg.value)
                    elif node.func.attr == 'subtract' and len(node.args) >= 2:
                        for arg in node.args[1:]:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                subtracts.append(arg.value)
        
        return variables, parameters, adds, subtracts
    
    def get_variable(self, variable_name: str) -> Optional[Dict]:
        """Get a specific variable's metadata"""
        if not self.variables_cache:
            self.load_all_variables()
        return self.variables_cache.get(variable_name)
    
    def search_variables(self, query: str) -> List[Dict]:
        """Search for variables matching a query"""
        if not self.variables_cache:
            self.load_all_variables()
        
        query_lower = query.lower()
        results = []
        
        for var_name, metadata in self.variables_cache.items():
            if query_lower in var_name.lower():
                results.append(metadata)
            elif metadata.get('label') and query_lower in metadata['label'].lower():
                results.append(metadata)
        
        return results