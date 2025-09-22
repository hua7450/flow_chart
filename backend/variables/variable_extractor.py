#!/usr/bin/env python3
"""
Variable extraction module for PolicyEngine variables.
Handles loading and parsing of variable definitions from Python files.
"""

import ast
import yaml
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
    
    def _load_parameter_list(self, param_path: str) -> List[str]:
        """Load a parameter list from a YAML file."""
        # Convert dot notation to file path
        # e.g., "gov.ssa.ssi.income.sources.earned" -> "../policyengine-us/policyengine_us/parameters/gov/ssa/ssi/income/sources/earned.yaml"
        param_file_path = Path("../policyengine-us/policyengine_us/parameters") / param_path.replace(".", "/")
        param_file_path = param_file_path.with_suffix(".yaml")
        
        try:
            with open(param_file_path, 'r') as f:
                data = yaml.safe_load(f)
                
            # Get the most recent values
            if 'values' in data:
                # Get the most recent date's values
                dates = sorted(data['values'].keys())
                if dates:
                    most_recent = dates[-1]
                    value = data['values'][most_recent]
                    if isinstance(value, list):
                        return value
                    
            return []
        except Exception as e:
            print(f"Error loading parameter list from {param_path}: {e}")
            return []
    
    def _extract_from_file(self, file_path: Path, variable_name: str) -> Optional[Dict]:
        """Extract variable metadata from a single file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # First, find any Enum class definitions
            enum_classes = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if this class inherits from Enum
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == 'Enum':
                            # Extract enum values
                            enum_values = self._extract_enum_values(node)
                            if enum_values:
                                enum_classes[node.name] = enum_values
            
            # Find the variable class definition
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == variable_name:
                    return self._extract_metadata(node, content, file_path, enum_classes)
        
        except Exception as e:
            # Skip files that can't be parsed
            # Uncomment for debugging:
            import traceback
            print(f"Error in {file_path}: {e}")
            traceback.print_exc()
            pass
        
        return None
    
    def _extract_metadata(self, class_node: ast.ClassDef, file_content: str, file_path: Path, enum_classes: Dict = None) -> Dict:
        """Extract metadata from a variable class definition."""
        if enum_classes is None:
            enum_classes = {}
        
        metadata = {
            'file_path': str(file_path),
            'parameters': {},
            'variables': [],
            'adds': [],
            'subtracts': [],
            'defined_for': [],
            'value_type': None,
            'possible_values': None,
            'enum_options': []
        }
        
        # Extract attributes from class body
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                self._extract_assignments(node, metadata, enum_classes)
            elif isinstance(node, ast.FunctionDef) and node.name == 'formula':
                metadata['variables'] = self._extract_formula_variables(node)
                metadata['parameters'] = self._extract_formula_parameters(node)
        
        # Don't add defined_for to variables list - it's handled separately in graph_builder
        # to show as a special type of dependency with different visualization
        
        # Expand parameter paths in adds/subtracts
        if 'adds_parameter' in metadata:
            param_path = metadata['adds_parameter']
            variable_list = self._load_parameter_list(param_path)
            if variable_list:
                metadata['adds'] = variable_list
                # Store the parameter path for display purposes
                metadata['adds_from_parameter'] = param_path
            del metadata['adds_parameter']
            
        if 'subtracts_parameter' in metadata:
            param_path = metadata['subtracts_parameter']
            variable_list = self._load_parameter_list(param_path)
            if variable_list:
                metadata['subtracts'] = variable_list
                # Store the parameter path for display purposes
                metadata['subtracts_from_parameter'] = param_path
            del metadata['subtracts_parameter']
        
        # Handle parameter lists (e.g., ["gov.states.il.dceo.liheap.payment.crisis_amount.max"])
        if 'adds_parameter_list' in metadata:
            param_paths = metadata['adds_parameter_list']
            # These are parameter paths that should be loaded as values, not variables
            metadata['adds_parameter_values'] = {}
            for param_path in param_paths:
                # Load the parameter value
                from parameters.parameter_handler import ParameterHandler
                param_handler = ParameterHandler()
                param_data = param_handler.load_parameter(param_path)
                if param_data:
                    # Format the value for display
                    value = param_handler.format_value(param_data, param_path.split('.')[-1], 'Summary')
                    metadata['adds_parameter_values'][param_path] = value
            del metadata['adds_parameter_list']
        
        if 'subtracts_parameter_list' in metadata:
            param_paths = metadata['subtracts_parameter_list']
            metadata['subtracts_parameter_values'] = {}
            for param_path in param_paths:
                from parameters.parameter_handler import ParameterHandler
                param_handler = ParameterHandler()
                param_data = param_handler.load_parameter(param_path)
                if param_data:
                    value = param_handler.format_value(param_data, param_path.split('.')[-1], 'Summary')
                    metadata['subtracts_parameter_values'][param_path] = value
            del metadata['subtracts_parameter_list']
        
        return metadata
    
    def _extract_assignments(self, node: ast.Assign, metadata: Dict, enum_classes: Dict = None) -> None:
        """Extract simple assignments from class body."""
        # Don't reassign enum_classes - use as is
        if enum_classes is None:
            enum_classes = {}
        for target in node.targets:
            if isinstance(target, ast.Name):
                attr_name = target.id
                
                # Handle defined_for specially (can be string or attribute)
                if attr_name == 'defined_for':
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        metadata['defined_for'] = node.value.value
                    elif isinstance(node.value, ast.Attribute):
                        # Handle attribute references like StateCode.DC
                        if isinstance(node.value.value, ast.Name):
                            metadata['defined_for'] = f"{node.value.value.id}.{node.value.attr}"
                
                # Handle adds/subtracts as strings (parameter paths)
                elif attr_name in ['adds', 'subtracts'] and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    # This is a parameter path like "gov.ssa.ssi.income.sources.earned"
                    # Store it with a special marker so we know to expand it later
                    if attr_name == 'adds':
                        metadata['adds_parameter'] = node.value.value
                    else:
                        metadata['subtracts_parameter'] = node.value.value
                
                # Extract string values
                elif isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    if attr_name == 'label':
                        metadata['label'] = node.value.value
                    elif attr_name == 'documentation':
                        metadata['description'] = node.value.value
                    elif attr_name == 'unit':
                        metadata['unit'] = node.value.value
                    elif attr_name == 'definition_period':
                        metadata['definition_period'] = node.value.value
                
                # Extract entity (e.g., Person, Household, TaxUnit, SPMUnit)
                elif attr_name == 'entity':
                    if isinstance(node.value, ast.Name):
                        metadata['entity'] = node.value.id

                # Extract value_type (e.g., Enum, float, int)
                elif attr_name == 'value_type':
                    if isinstance(node.value, ast.Name):
                        metadata['value_type'] = node.value.id

                # Extract possible_values (for Enum types)
                elif attr_name == 'possible_values':
                    if isinstance(node.value, ast.Name):
                        enum_class_name = node.value.id
                        metadata['possible_values'] = enum_class_name
                        # Look up the enum values if we found the class
                        if enum_classes and enum_class_name in enum_classes:
                            metadata['enum_options'] = enum_classes[enum_class_name]
                
                # Extract list values
                elif isinstance(node.value, ast.List):
                    items = []
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            items.append(elt.value)
                    
                    if attr_name == 'adds':
                        # Check if items contain parameter paths (they contain dots and start with 'gov')
                        if items and all('.' in item and item.startswith('gov') for item in items):
                            # These are parameter paths, not variable names
                            # We'll handle them separately
                            metadata['adds_parameter_list'] = items
                        else:
                            metadata['adds'] = items
                    elif attr_name == 'subtracts':
                        # Same check for subtracts
                        if items and all('.' in item and item.startswith('gov') for item in items):
                            metadata['subtracts_parameter_list'] = items
                        else:
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
                
                # Handle entity.other_entity() calls: person.household('variable_name', ...), spm_unit.household(), etc.
                elif isinstance(node.func, ast.Attribute):
                    # List of all entity types
                    entity_types = ['person', 'tax_unit', 'household', 'family', 'spm_unit', 'marital_unit', 
                                   'members', 'group', 'unit']
                    
                    # Check if it's entity.other_entity pattern (or entity.members pattern)
                    if isinstance(node.func.value, ast.Name):
                        # Check if both the base and attribute are entity-related
                        if (node.func.value.id in entity_types or 
                            node.func.value.id.endswith('_unit') or  # Catch any custom unit types
                            node.func.value.id.endswith('_group')):
                            if node.func.attr in entity_types:
                                if node.args and isinstance(node.args[0], ast.Constant):
                                    variables.append(node.args[0].value)
                    
                    # Also check for chained entity access like person.spm_unit.household('variable_name')
                    elif isinstance(node.func.value, ast.Attribute):
                        # This could be a longer chain, but if it ends with an entity method, extract the variable
                        if node.func.attr in entity_types:
                            if node.args and isinstance(node.args[0], ast.Constant):
                                variables.append(node.args[0].value)
                    
                    # Handle .variable() or .get_variable() method calls
                    if node.func.attr in ['variable', 'get_variable']:
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
                        # Look for both types of parameter assignments
                        if isinstance(node.value, ast.Attribute):
                            # Extract the parameter path
                            param_path = self._extract_parameter_path(node.value)
                            if param_path:
                                # Any assignment of parameters(period).xxx is a parameter
                                # Store it as a direct parameter assignment
                                parameters[target.id] = param_path
                                # Also track it as a parameter variable for potential sub-attribute access
                                param_var_assignments[target.id] = param_path
                        elif isinstance(node.value, ast.Subscript):
                            # Handle subscripted parameters like parameters(period).gov.hhs.smi.amount[state]
                            if isinstance(node.value.value, ast.Attribute):
                                param_path = self._extract_parameter_path(node.value.value)
                                if param_path:
                                    # Extract the parameter name from the path
                                    param_name = param_path.split('.')[-1]
                                    parameters[param_name] = param_path
        
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
                # Check if this is a parameter usage like p.rent_rate or p.entry.fpg_limit.preschool
                # Build the full chain from this attribute node
                chain = []
                current = node
                while isinstance(current, ast.Attribute):
                    chain.append(current.attr)
                    current = current.value
                
                # Check if the base is a parameter variable (like 'p')
                if isinstance(current, ast.Name) and current.id in param_var_assignments:
                    chain.reverse()  # Now chain is ['entry', 'fpg_limit', 'preschool'] for p.entry.fpg_limit.preschool
                    base_path = param_var_assignments[current.id]
                    
                    # Combine base path with the attribute chain
                    full_param_path = base_path
                    for part in chain:
                        full_param_path = f"{full_param_path}.{part}"
                    
                    # Use the last part as the parameter name (e.g., 'preschool')
                    param_name = chain[-1] if chain else node.attr
                    parameters[param_name] = full_param_path
            
            elif isinstance(node, ast.Subscript):
                # Handle subscripted parameter access like p.electricity[housing_type][income_level][capped_size]
                # or p_fpg.first_person[state_group]
                # Walk up to find the base parameter reference
                current = node
                while isinstance(current, ast.Subscript):
                    current = current.value
                
                # Check if this is a parameter attribute
                if isinstance(current, ast.Attribute):
                    # Build the full chain back from this attribute
                    attr_chain = []
                    attr_current = current
                    while isinstance(attr_current, ast.Attribute):
                        attr_chain.append(attr_current.attr)
                        attr_current = attr_current.value
                    
                    # Check if the base is a parameter variable
                    if isinstance(attr_current, ast.Name) and attr_current.id in param_var_assignments:
                        attr_chain.reverse()  # Now chain is in correct order
                        base_path = param_var_assignments[attr_current.id]
                        
                        # Combine base path with the attribute chain
                        full_param_path = base_path
                        for part in attr_chain:
                            full_param_path = f"{full_param_path}.{part}"
                        
                        # Use the last part as the parameter name (e.g., 'first_person')
                        param_name = attr_chain[-1] if attr_chain else current.attr
                        parameters[param_name] = full_param_path
        
        # Consolidate parameters from the same base path
        # For example, if we have first_person and additional_person both from fpg,
        # we should just have fpg as the parameter
        # But for parameters like dc_liheap_payment which has electricity, gas, oil, heat_in_rent,
        # we want to keep them separate for display
        consolidated = {}
        base_params = {}
        
        for param_name, param_path in parameters.items():
            # Check if this is a sub-parameter of a larger parameter
            path_parts = param_path.split('.')
            if len(path_parts) > 1:
                # Get the base parameter name (e.g., 'fpg' from 'gov.hhs.fpg.first_person')
                base_param = '.'.join(path_parts[:-1])
                if base_param not in base_params:
                    base_params[base_param] = []
                base_params[base_param].append(param_name)
        
        # Decide whether to consolidate or keep sub-parameters separate
        # Heuristic: If we have 2-4 sub-parameters, they likely represent distinct values (like max/min or different categories)
        # If we have many (>4), they might be better consolidated
        # Never consolidate if it would lose important information
        
        for base_param, sub_params in base_params.items():
            if len(sub_params) == 1:
                # Single sub-parameter - keep as is
                for sub_param in sub_params:
                    consolidated[sub_param] = parameters[sub_param]
            elif len(sub_params) <= 4:
                # Small number of sub-parameters - keep them separate
                # These likely represent distinct meaningful values (max/min, different utilities, etc.)
                for sub_param in sub_params:
                    consolidated[sub_param] = parameters[sub_param]
            else:
                # Many sub-parameters - consider consolidating
                # But check if they seem like distinct categories first
                # If all sub-params are short common words, keep separate
                all_short = all(len(sp) <= 10 for sp in sub_params)
                if all_short:
                    # These are likely meaningful distinct categories
                    for sub_param in sub_params:
                        consolidated[sub_param] = parameters[sub_param]
                else:
                    # Consolidate to base parameter
                    param_name = base_param.split('.')[-1]
                    consolidated[param_name] = base_param
        
        # Add any parameters that weren't part of consolidation
        for param_name, param_path in parameters.items():
            if param_name not in consolidated and not any(param_name in subs for subs in base_params.values()):
                consolidated[param_name] = param_path
        
        return consolidated if consolidated else parameters
    
    def _extract_enum_values(self, enum_node: ast.ClassDef) -> List[Dict[str, str]]:
        """Extract enum values from an Enum class definition."""
        enum_values = []
        
        for node in enum_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        enum_key = target.id
                        enum_value = None
                        
                        # Extract the value (usually a string)
                        if isinstance(node.value, ast.Constant):
                            enum_value = node.value.value
                        
                        if enum_key and enum_value:
                            enum_values.append({
                                'key': enum_key,
                                'value': enum_value
                            })
        
        return enum_values
    
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