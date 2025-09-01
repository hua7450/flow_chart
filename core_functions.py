#!/usr/bin/env python3
"""
Core functions for PolicyEngine Flowchart Visualizer
These are the same functions from app.py but without Streamlit decorators
"""

import ast
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import yaml
from datetime import datetime
import re

def load_variables():
    """Load all variables from PolicyEngine source files without caching."""
    variables = {}
    
    # Look for PolicyEngine US source files
    policyengine_path = Path("policyengine-us/policyengine_us/variables")
    
    if not policyengine_path.exists():
        print(f"Path not found: {policyengine_path}")
        return variables
    
    # Recursively find all Python files
    python_files = list(policyengine_path.rglob("*.py"))
    
    for file_path in python_files:
        if "__pycache__" in str(file_path):
            continue
            
        # Extract variable name from file path
        # e.g. "household/income/household_net_income.py" -> "household_net_income"
        variable_name = file_path.stem
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Parse the Python file
            tree = ast.parse(content)
            
            # Find the variable class definition
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == variable_name:
                    # Extract variable metadata
                    variables[variable_name] = extract_variable_metadata(node, content, file_path)
                    break
        except Exception as e:
            # Skip files that can't be parsed
            continue
    
    return variables

def extract_variable_metadata(class_node, file_content, file_path):
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
        # Get simple string assignments
        if isinstance(node, ast.Assign):
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
        
        # Extract formula method
        elif isinstance(node, ast.FunctionDef) and node.name == 'formula':
            metadata['variables'] = extract_formula_variables(node, file_content)
            metadata['parameters'] = extract_formula_parameters(node, file_content)
    
    return metadata

def extract_formula_variables(formula_node, file_content):
    """Extract variable references from formula method."""
    variables = []
    
    for node in ast.walk(formula_node):
        # Look for patterns like: variable('variable_name', ...)
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Attribute) and 
                node.func.attr in ['variable', 'get_variable']):
                # First argument is the variable name
                if node.args and isinstance(node.args[0], ast.Constant):
                    variables.append(node.args[0].value)
            
            # Also look for direct method calls on the first parameter
            # e.g. tax_unit('variable_name', ...)
            elif (isinstance(node.func, ast.Name) and 
                  node.func.id in ['person', 'tax_unit', 'household', 'family', 'spm_unit']):
                if node.args and isinstance(node.args[0], ast.Constant):
                    variables.append(node.args[0].value)
    
    return list(set(variables))  # Remove duplicates

def extract_formula_parameters(formula_node, file_content):
    """Extract parameter references from formula method."""
    parameters = {}
    
    for node in ast.walk(formula_node):
        # Look for patterns like: parameters(period).path.to.parameter
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Attribute) and 
                node.func.attr in ['parameter', 'get_parameter']):
                # Try to extract the parameter path from the arguments
                if node.args and isinstance(node.args[0], ast.Constant):
                    param_path = node.args[0].value
                    param_name = param_path.split('.')[-1]
                    parameters[param_name] = param_path
            
            # Also check for direct parameter access
            elif isinstance(node.func, ast.Name) and node.func.id == 'parameters':
                # This typically returns a parameter node that gets accessed
                # We need to trace the attribute chain after it
                # This is complex to do statically, so we'll skip for now
                pass
    
    return parameters

def load_parameter_file(param_path: str) -> Optional[Dict]:
    """Load a parameter YAML file without caching."""
    # Look for parameter files in the parameters directory
    base_paths = [
        Path("policyengine-us/policyengine_us/parameters"),
        Path("policyengine-us/policyengine_us/data/parameters")
    ]
    
    # Convert dot notation to path
    path_parts = param_path.replace('.yaml', '').split('.')
    
    for base_path in base_paths:
        yaml_path = base_path / Path(*path_parts[:-1]) / f"{path_parts[-1]}.yaml"
        
        if yaml_path.exists():
            try:
                with open(yaml_path, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Error loading {yaml_path}: {e}")
    
    return None

def format_parameter_value(param_data: Dict, param_name: str, detail_level: str = "Summary") -> str:
    """Format parameter value for display."""
    if 'values' in param_data:
        values = param_data['values']
        
        if detail_level == "Summary":
            # Show just the latest value
            latest_date, latest_value = get_latest_value(values)
            return f"{latest_value} (as of {latest_date})"
        
        elif detail_level == "Latest 5 values":
            # Show the 5 most recent values
            sorted_dates = sorted(values.keys(), reverse=True)[:5]
            value_strs = []
            for date in sorted_dates:
                value_strs.append(f"{date}: {values[date]}")
            return "\n".join(value_strs)
        
        elif detail_level == "All values":
            # Show all values
            sorted_dates = sorted(values.keys(), reverse=True)
            value_strs = []
            for date in sorted_dates:
                value_strs.append(f"{date}: {values[date]}")
            return "\n".join(value_strs[:20])  # Limit to 20 for display
    
    return "No value data"

def detect_parameter_structure(param_data: Dict) -> str:
    """Detect the structure of parameter data."""
    if 'values' in param_data:
        values = param_data['values']
        if values:
            sample_value = list(values.values())[0]
            if isinstance(sample_value, dict):
                return "brackets"
            elif isinstance(sample_value, list):
                return "list"
            else:
                return "scalar"
    elif 'brackets' in param_data:
        return "brackets"
    
    return "unknown"

def get_latest_value(values: Dict) -> tuple:
    """Get the latest value from a values dictionary."""
    if not values:
        return None, None
    
    # Sort dates and get the most recent
    sorted_dates = sorted(values.keys(), reverse=True)
    latest_date = sorted_dates[0]
    latest_value = values[latest_date]
    
    return latest_date, latest_value

def build_dependency_graph(variables: Dict, 
                          start_variable: str,
                          max_depth: int = 10,
                          stop_variables: Set[str] = None,
                          expand_adds_subtracts: bool = True,
                          show_parameters: bool = True,
                          param_detail_level: str = "Summary",
                          param_date: Optional[str] = None,
                          no_params_list: List[str] = None) -> Dict:
    """Build a dependency graph for visualization."""
    if stop_variables is None:
        stop_variables = set()
    if no_params_list is None:
        no_params_list = []
    
    nodes = {}
    edges = []
    visited = set()
    
    def add_dependencies(var_name: str, level: int = 0):
        if var_name in visited or level > max_depth:
            return
        
        visited.add(var_name)
        
        # Check if this is a stop variable
        is_stop = var_name in stop_variables
        
        # Add node
        if var_name not in nodes:
            var_data = variables.get(var_name, {})
            
            # Build title/tooltip
            title_parts = [f"<b>{var_name}</b>"]
            if 'label' in var_data:
                title_parts.append(f"Label: {var_data['label']}")
            if 'description' in var_data:
                title_parts.append(f"Description: {var_data['description'][:200]}...")
            
            # Add parameters to title if enabled
            if show_parameters and var_data.get('parameters') and var_name not in no_params_list:
                title_parts.append("<br><b>Parameters:</b>")
                for param_name, param_path in var_data['parameters'].items():
                    param_data = load_parameter_file(param_path)
                    if param_data:
                        param_value = format_parameter_value(param_data, param_name, param_detail_level)
                        title_parts.append(f"• {param_name}: {param_value}")
            
            nodes[var_name] = {
                'level': level,
                'type': 'stop' if is_stop else 'variable',
                'title': "<br>".join(title_parts),
                'data': var_data
            }
        
        # Don't expand stop variables
        if is_stop:
            return
        
        # Add dependencies
        if var_name in variables:
            var_data = variables[var_name]
            
            # Add regular variable dependencies
            for dep_var in var_data.get('variables', []):
                if dep_var != var_name:  # Avoid self-references
                    edges.append({
                        'from': dep_var,
                        'to': var_name,
                        'type': 'depends'
                    })
                    add_dependencies(dep_var, level + 1)
            
            # Add adds/subtracts if enabled
            if expand_adds_subtracts:
                for add_var in var_data.get('adds', []):
                    if add_var != var_name:
                        edges.append({
                            'from': add_var,
                            'to': var_name,
                            'type': 'adds'
                        })
                        add_dependencies(add_var, level + 1)
                
                for sub_var in var_data.get('subtracts', []):
                    if sub_var != var_name:
                        edges.append({
                            'from': sub_var,
                            'to': var_name,
                            'type': 'subtracts'
                        })
                        add_dependencies(sub_var, level + 1)
    
    # Start building from the target variable
    add_dependencies(start_variable, 0)
    
    return {
        'nodes': nodes,
        'edges': edges
    }