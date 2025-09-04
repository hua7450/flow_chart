#!/usr/bin/env python3
"""
Variable extraction module for PolicyEngine variables.
Handles loading and parsing of variable definitions from Python files.
"""

import ast
from pathlib import Path
from typing import Dict, List, Set, Optional, Any


class VariableExtractor:
    """Extracts PolicyEngine variables from source files."""
    
    def __init__(self, base_path: str = "../policyengine-us/policyengine_us/variables"):
        self.base_path = Path(base_path)
    
    def load_all_variables(self) -> Dict[str, Dict]:
        """Load all variables from PolicyEngine source files."""
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
    
    def _extract_from_file(self, file_path: Path, variable_name: str) -> Optional[Dict]:
        """Extract variable metadata from a single file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Find the variable class definition
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == variable_name:
                    return self._extract_metadata(node, content, file_path)
        
        except Exception as e:
            # Skip files that can't be parsed
            pass
        
        return None
    
    def _extract_metadata(self, class_node: ast.ClassDef, file_content: str, file_path: Path) -> Dict:
        """Extract metadata from a variable class definition."""
        metadata = {
            'file_path': str(file_path),
            'parameters': {},
            'variables': [],
            'adds': [],
            'subtracts': [],
            'defined_for': []
        }
        
        # Extract attributes from class body
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                self._extract_assignments(node, metadata)
            elif isinstance(node, ast.FunctionDef) and node.name == 'formula':
                metadata['variables'] = self._extract_formula_variables(node)
                metadata['parameters'] = self._extract_formula_parameters(node)
        
        return metadata
    
    def _extract_assignments(self, node: ast.Assign, metadata: Dict) -> None:
        """Extract simple assignments from class body."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                attr_name = target.id
                
                # Extract string values
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    if attr_name == 'label':
                        metadata['label'] = node.value.value
                    elif attr_name == 'documentation':
                        metadata['description'] = node.value.value
                    elif attr_name == 'unit':
                        metadata['unit'] = node.value.value
                    elif attr_name == 'definition_period':
                        metadata['definition_period'] = node.value.value
                
                # Extract list values
                elif isinstance(node.value, ast.List):
                    items = []
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            items.append(elt.value)
                    
                    if attr_name == 'adds':
                        metadata['adds'] = items
                    elif attr_name == 'subtracts':
                        metadata['subtracts'] = items
                    elif attr_name == 'defined_for':
                        metadata['defined_for'] = items
                
                # Handle list comprehensions (e.g., ["social_security_" + i for i in [...]])
                elif isinstance(node.value, ast.ListComp):
                    items = self._evaluate_list_comprehension(node.value)
                    if items:
                        if attr_name == 'adds':
                            metadata['adds'] = items
                        elif attr_name == 'subtracts':
                            metadata['subtracts'] = items
    
    def _extract_formula_variables(self, formula_node: ast.FunctionDef) -> List[str]:
        """Extract variable references from formula method."""
        variables = []
        
        # First pass: collect all constant list assignments and list comprehensions
        list_vars = {}
        for node in ast.walk(formula_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Handle list comprehensions
                        if isinstance(node.value, ast.ListComp):
                            # Try to resolve the list comprehension
                            comp_result = self._evaluate_list_comprehension_with_context(node.value, formula_node)
                            if comp_result:
                                list_vars[target.id] = comp_result
                        # Handle constant lists
                        elif isinstance(node.value, ast.List):
                            items = []
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant):
                                    items.append(elt.value)
                            if items:
                                list_vars[target.id] = items
        
        # Second pass: extract variable references
        for node in ast.walk(formula_node):
            if isinstance(node, ast.Call):
                # Handle entity calls: person('variable_name', ...)
                if (isinstance(node.func, ast.Name) and 
                    node.func.id in ['person', 'tax_unit', 'household', 'family', 'spm_unit', 'marital_unit']):
                    if node.args and isinstance(node.args[0], ast.Constant):
                        variables.append(node.args[0].value)
                
                # Handle .variable() method calls
                elif (isinstance(node.func, ast.Attribute) and 
                      node.func.attr in ['variable', 'get_variable']):
                    if node.args and isinstance(node.args[0], ast.Constant):
                        variables.append(node.args[0].value)
                
                # Handle add() function: add(entity, period, ["var1", "var2"])
                elif isinstance(node.func, ast.Name) and node.func.id == 'add':
                    if len(node.args) >= 3:
                        # Handle list of variables
                        if isinstance(node.args[2], ast.List):
                            for elt in node.args[2].elts:
                                if isinstance(elt, ast.Constant):
                                    variables.append(elt.value)
                        # Handle single variable as string
                        elif isinstance(node.args[2], ast.Constant):
                            variables.append(node.args[2].value)
                        # Handle variable name that references a list
                        elif isinstance(node.args[2], ast.Name):
                            var_name = node.args[2].id
                            if var_name in list_vars:
                                variables.extend(list_vars[var_name])
                
                # Handle select() with variable references
                elif isinstance(node.func, ast.Name) and node.func.id in ['select', 'where']:
                    # These often contain variable references in their conditions
                    pass
        
        return list(set(variables))  # Remove duplicates
    
    def _evaluate_list_comprehension_with_context(self, node: ast.ListComp, formula_node: ast.FunctionDef) -> List[str]:
        """Evaluate list comprehensions with access to formula context."""
        # First try the regular evaluation
        result = self._evaluate_list_comprehension(node)
        if result:
            return result
        
        # If that fails, try to resolve variable references in the comprehension
        if len(node.generators) == 1:
            generator = node.generators[0]
            
            # Look for the iterator variable in the formula's assignments
            if isinstance(generator.iter, ast.Name):
                iter_var_name = generator.iter.id
                # Find the assignment in the formula
                for stmt in formula_node.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name) and target.id == iter_var_name:
                                if isinstance(stmt.value, ast.List):
                                    # Found the list definition, now evaluate the comprehension
                                    items = []
                                    for elt in stmt.value.elts:
                                        if isinstance(elt, ast.Constant):
                                            # Apply the comprehension expression
                                            if isinstance(node.elt, ast.BinOp) and isinstance(node.elt.op, ast.Add):
                                                # Handle i.lower() + "_suffix" pattern
                                                if isinstance(node.elt.left, ast.Call):
                                                    if (isinstance(node.elt.left.func, ast.Attribute) and
                                                        node.elt.left.func.attr == 'lower' and
                                                        isinstance(node.elt.right, ast.Constant)):
                                                        suffix = node.elt.right.value
                                                        items.append(elt.value.lower() + suffix)
                                    return items
        return []
    
    def _evaluate_list_comprehension(self, node: ast.ListComp) -> List[str]:
        """Evaluate simple list comprehensions to extract string values."""
        try:
            # Handle simple case: ["prefix_" + i for i in ["a", "b", "c"]]
            if (isinstance(node.elt, ast.BinOp) and 
                isinstance(node.elt.op, ast.Add) and
                len(node.generators) == 1):
                
                generator = node.generators[0]
                # Check if iterating over a list of strings
                if isinstance(generator.iter, ast.List):
                    items = []
                    for elt in generator.iter.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            # Evaluate the expression for each item
                            if isinstance(node.elt.left, ast.Constant):
                                prefix = node.elt.left.value
                                items.append(prefix + elt.value)
                            elif isinstance(node.elt.right, ast.Constant):
                                suffix = node.elt.right.value
                                items.append(elt.value + suffix)
                    return items
                # Check if iterating over a variable (e.g., STATES_WITH_CHILD_CARE_SUBSIDIES)
                elif isinstance(generator.iter, ast.Name):
                    # For now, we can't resolve variable references, but we could enhance this
                    # to look for the variable definition in the same function
                    pass
            
            # Handle case: [i.lower() + "_suffix" for i in ["CA", "CO", "NE"]]
            elif (len(node.generators) == 1):
                generator = node.generators[0]
                if isinstance(generator.iter, ast.List):
                    items = []
                    for elt in generator.iter.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            # Handle method calls like i.lower()
                            if isinstance(node.elt, ast.BinOp) and isinstance(node.elt.op, ast.Add):
                                if isinstance(node.elt.left, ast.Call):
                                    # e.g., i.lower() + "_suffix"
                                    if (isinstance(node.elt.left.func, ast.Attribute) and
                                        node.elt.left.func.attr == 'lower' and
                                        isinstance(node.elt.right, ast.Constant)):
                                        suffix = node.elt.right.value
                                        items.append(elt.value.lower() + suffix)
                    return items
        except:
            pass
        return []
    
    def _extract_formula_parameters(self, formula_node: ast.FunctionDef) -> Dict[str, str]:
        """Extract parameter references from formula method."""
        parameters = {}
        param_var_assignments = {}  # Track parameter variable assignments like p = parameters(...)
        
        # First pass: identify parameter variable assignments
        for node in ast.walk(formula_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Look for assignments like: p = parameters(period).gov.states.il.dceo.liheap.eligibility
                        if isinstance(node.value, ast.Attribute):
                            param_path = self._extract_parameter_path(node.value)
                            if param_path:
                                param_var_assignments[target.id] = param_path
        
        # Second pass: find actual parameter usage (e.g., p.rent_rate)
        for node in ast.walk(formula_node):
            if isinstance(node, ast.Call):
                # Handle .parameter() method calls
                if (isinstance(node.func, ast.Attribute) and 
                    node.func.attr in ['parameter', 'get_parameter']):
                    if node.args and isinstance(node.args[0], ast.Constant):
                        param_path = node.args[0].value
                        param_name = param_path.split('.')[-1]
                        parameters[param_name] = param_path
            
            elif isinstance(node, ast.Attribute):
                # Check if this is a parameter usage like p.rent_rate
                if (isinstance(node.value, ast.Name) and 
                    node.value.id in param_var_assignments):
                    base_path = param_var_assignments[node.value.id]
                    full_param_path = f"{base_path}.{node.attr}"
                    param_name = node.attr  # Use the actual parameter name
                    parameters[param_name] = full_param_path
        
        return parameters
    
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