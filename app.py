#!/usr/bin/env python3
"""
PolicyEngine Variable Dependency Flowchart Visualizer
A Streamlit web app that generates interactive dependency flowcharts for PolicyEngine variables.
"""

import streamlit as st
import ast
from pathlib import Path
from pyvis.network import Network
import tempfile
from typing import Dict, List, Set, Optional, Tuple, Any
import yaml
from datetime import datetime
import re

# Import stop variables configuration
from stop_variables_config import DEFAULT_STOP_VARIABLES

# Page config
st.set_page_config(
    page_title="PolicyEngine Variable Dependency Visualizer",
    page_icon="📊",
    layout="wide"
)

# Cache the variables data (clear cache if code changes)
@st.cache_data(ttl=300)  # Cache for 5 minutes only
def load_variables():
    """Load variables directly from the PolicyEngine submodule."""
    variables_dir = Path(__file__).parent / "policyengine-us" / "policyengine_us" / "variables"
    
    if not variables_dir.exists():
        # Try to initialize submodule automatically
        try:
            import subprocess
            import os
            
            # Change to the app directory
            app_dir = Path(__file__).parent
            result = subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive"],
                cwd=app_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0 and variables_dir.exists():
                st.success("✅ Successfully initialized PolicyEngine submodule!")
                # Rerun to load variables
                st.rerun()
            else:
                st.error(f"Failed to initialize submodule. Return code: {result.returncode}")
                st.error(f"Error: {result.stderr}")
                
        except Exception as e:
            st.error(f"Error initializing submodule: {str(e)}")
            
        st.error(f"Variables directory not found at: {variables_dir}")
        st.info("Please ensure the git submodule is initialized:")
        st.code("git submodule update --init --recursive")
        return {}
    
    variables_data = {}
    
    # Walk through all Python files in the variables directory
    for py_file in variables_dir.glob("**/*.py"):
        if py_file.name.startswith("__"):
            continue
            
        try:
            # Parse the Python file to extract variable information
            var_data = parse_variable_file(py_file)
            if var_data:
                var_name = py_file.stem
                variables_data[var_name] = var_data
        except Exception:
            # Skip files that can't be parsed
            continue
    
    return variables_data

def parse_variable_file(file_path: Path) -> Optional[Dict]:
    """Parse a Python variable file to extract metadata."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        # Find the Variable class definition
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                isinstance(base, ast.Name) and base.id == "Variable" 
                for base in node.bases
            ):
                return extract_variable_metadata(node, file_path)
        
        return None
        
    except Exception:
        return None

def extract_variable_metadata(class_node: ast.ClassDef, file_path: Path) -> Dict:
    """Extract metadata from a Variable class AST node."""
    metadata = {
        "file_path": str(file_path.relative_to(Path(__file__).parent)),
        "formula": None,
        "adds": [],
        "subtracts": [],
        "parameters": {},  # Changed to dict to store parameter paths
        "variables": [],
        "defined_for": [],
        "description": None,
        "label": None,
        "unit": None
    }
    
    # Extract class attributes
    for node in class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    attr_name = target.id
                    value = extract_ast_value(node.value)
                    
                    if attr_name == "label" and isinstance(value, str):
                        metadata["label"] = value
                    elif attr_name == "documentation" and isinstance(value, str):
                        metadata["description"] = value
                    elif attr_name == "adds":
                        if isinstance(value, list):
                            metadata["adds"] = value
                        elif isinstance(value, str) and value.startswith("gov."):
                            # This is a parameter path
                            metadata["parameters"]["adds_sources"] = value
                        else:
                            metadata["adds"] = [value] if value else []
                    elif attr_name == "subtracts":
                        if isinstance(value, list):
                            metadata["subtracts"] = value
                        elif isinstance(value, str) and value.startswith("gov."):
                            # This is a parameter path
                            metadata["parameters"]["subtracts_sources"] = value
                        else:
                            metadata["subtracts"] = [value] if value else []
                    elif attr_name == "defined_for":
                        if isinstance(value, str):
                            metadata["defined_for"] = [value]
                        elif isinstance(value, list):
                            metadata["defined_for"] = value
        
        elif isinstance(node, ast.FunctionDef) and node.name == "formula":
            # Extract variables and parameters used in the formula
            formula_vars = extract_formula_variables(node)
            metadata["variables"] = formula_vars
            # Extract parameter usage
            param_info = extract_formula_parameters(node)
            metadata["parameters"] = param_info
    
    return metadata

def extract_ast_value(node):
    """Extract Python value from AST node."""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.List):
        return [extract_ast_value(item) for item in node.elts]
    elif isinstance(node, ast.Name):
        return node.id
    else:
        try:
            return str(ast.unparse(node)) if hasattr(ast, 'unparse') else None
        except:
            return None

def extract_formula_variables(func_node: ast.FunctionDef) -> List[str]:
    """Extract variable names used in a formula function."""
    variables = set()
    
    for node in ast.walk(func_node):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            # Handle cases like person("variable_name", period)
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                variables.add(node.slice.value)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            # Handle direct function calls that might reference variables
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    # This might be a variable name
                    if "_" in arg.value or arg.value.islower():
                        variables.add(arg.value)
    
    return list(variables)

def extract_formula_parameters(func_node: ast.FunctionDef) -> Dict[str, str]:
    """Extract parameter paths used in a formula function."""
    parameters = {}
    param_vars = {}  # Track variable assignments like p = parameters(period).gov...
    
    # First pass: find parameter assignments
    for node in ast.walk(func_node):
        if isinstance(node, ast.Assign):
            # Check for p = parameters(period).gov...
            if (len(node.targets) == 1 and 
                isinstance(node.targets[0], ast.Name)):
                var_name = node.targets[0].id
                
                # Check if this is a parameters() call
                if isinstance(node.value, ast.Attribute):
                    # Traverse the chain to build the full path
                    path_parts = []
                    current = node.value
                    
                    while isinstance(current, ast.Attribute):
                        path_parts.insert(0, current.attr)
                        current = current.value
                    
                    if (isinstance(current, ast.Call) and 
                        isinstance(current.func, ast.Name) and 
                        current.func.id == "parameters"):
                        # This is a parameters(period) call
                        param_vars[var_name] = ".".join(path_parts)
    
    # Second pass: find parameter usage
    for node in ast.walk(func_node):
        if isinstance(node, ast.Attribute):
            # Check for p.electricity, p.water, etc.
            if (isinstance(node.value, ast.Name) and 
                node.value.id in param_vars):
                # This is using a parameter variable
                base_path = param_vars[node.value.id]
                full_path = f"{base_path}.{node.attr}"
                # Use the attribute name as key for easy reference
                parameters[node.attr] = full_path
    
    return parameters

# Cache parameter files
@st.cache_data
def load_parameter_file(param_path: str) -> Optional[Dict]:
    """Load a parameter YAML file from the PolicyEngine parameters directory."""
    try:
        # Convert dot path to file path
        # gov.local.ca.riv.cap.share.payment.electricity -> 
        # parameters/gov/local/ca/riv/cap/share/payment/electricity.yaml
        path_parts = param_path.split(".")
        yaml_path = Path(__file__).parent / "policyengine-us" / "policyengine_us" / "parameters"
        for part in path_parts:
            yaml_path = yaml_path / part
        yaml_path = yaml_path.with_suffix(".yaml")
        
        if not yaml_path.exists():
            return None
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        st.warning(f"Could not load parameter {param_path}: {str(e)}")
        return None

def detect_parameter_structure(param_data: Dict) -> str:
    """Detect the structure type of a parameter file."""
    if not param_data:
        return "unknown"
    
    # Check for standard keys
    if "values" in param_data:
        values = param_data["values"]
        # Get the first date key's value
        first_value = next(iter(values.values())) if values else None
        if isinstance(first_value, list):
            return "list"
        else:
            return "simple"
    elif "brackets" in param_data:
        return "brackets"
    
    # Check the non-metadata keys
    data_keys = [k for k in param_data.keys() if k not in ["metadata", "description"]]
    if not data_keys:
        return "empty"
    
    sample_key = data_keys[0]
    
    # Check if numeric indexed
    if str(sample_key).isdigit():
        return "numeric_index"
    
    # Check if category based (uppercase keys)
    if isinstance(sample_key, str) and sample_key.isupper():
        # Check nesting depth
        sample_value = param_data[sample_key]
        if isinstance(sample_value, dict):
            sub_keys = [k for k in sample_value.keys() if k != "metadata"]
            if sub_keys:
                sub_key = sub_keys[0]
                if str(sub_key).isdigit():
                    # Like LIHEAP - housing type -> income level -> household size
                    return "nested_3_level"
                elif isinstance(sub_key, str) and sub_key.isupper():
                    # Like reimbursement rates
                    return "nested_3_level_category"
        return "category"
    
    return "unknown"

def get_latest_value(value_data: Any, period: Optional[str] = None) -> Any:
    """Get the latest value from a time-series parameter value."""
    if not isinstance(value_data, dict):
        return value_data
    
    # If it's a dict with date keys (could be strings or datetime objects)
    date_keys = []
    for key in value_data.keys():
        # Check if it's a datetime.date object
        if hasattr(key, 'year') and hasattr(key, 'month') and hasattr(key, 'day'):
            date_keys.append(key)
        # Check if this looks like a date string (YYYY-MM-DD format)
        elif isinstance(key, str) and len(key) == 10 and key[4] == "-" and key[7] == "-":
            try:
                # Verify it's a valid date format
                year, month, day = key.split("-")
                if year.isdigit() and month.isdigit() and day.isdigit():
                    date_keys.append(key)
            except:
                pass
    
    if date_keys:
        # Sort dates and get the latest
        date_keys.sort()
        if period:
            # Find the value for the specified period or closest before
            # Convert period string to comparable format if needed
            for date in reversed(date_keys):
                # Compare appropriately based on type
                if (isinstance(date, str) and date <= period) or \
                   (hasattr(date, 'strftime') and date.strftime("%Y-%m-%d") <= period):
                    return value_data[date]
        # Return the latest value
        return value_data[date_keys[-1]]
    
    return value_data

def format_parameter_value(param_data: Dict, param_name: str, detail_level: str = "Summary") -> str:
    """Format a parameter value for display based on its structure."""
    if not param_data:
        return "Parameter not found"
    
    structure = detect_parameter_structure(param_data)
    metadata = param_data.get("metadata", {})
    unit = metadata.get("unit", "")
    label = metadata.get("label", param_name)
    
    if structure == "simple":
        value = get_latest_value(param_data["values"])
        if isinstance(value, dict):
            # Still has nested structure, get the actual value
            value = next(iter(value.values())) if value else 0
        
        if unit == "currency-USD":
            return f"${value:,}"
        elif unit == "/1":
            if isinstance(value, (int, float)):
                return f"{value:.1%}" if value < 1 else f"{value:.0%}"
            else:
                return str(value)
        else:
            return str(value)
    
    elif structure == "list":
        values = get_latest_value(param_data["values"])
        if not values:
            return "Empty list"
        
        # Format list items - show ALL items as requested
        formatted_items = []
        
        # Check if this is a list of variable names (for adds/subtracts sources)
        is_variable_list = all(isinstance(item, str) and "_" in item and not item.isupper() for item in values[:3] if values)
        
        if detail_level == "Minimal":
            # Show count only
            return f"{len(values)} items"
        elif detail_level == "Summary":
            # Show all items but compact
            for item in values:
                if isinstance(item, str) and item.isupper():
                    # Format enum-like values
                    readable = item.replace("_", " ").title()
                    formatted_items.append(readable)
                else:
                    formatted_items.append(str(item))
            
            # For variable lists, show each on new line for clarity
            if is_variable_list and len(values) <= 5:
                return "\n    - " + "\n    - ".join(formatted_items)
            elif len(values) > 10:
                return f"({len(values)} items): {', '.join(formatted_items)}"
            else:
                return ", ".join(formatted_items)
        else:  # Full
            # Show all items with line breaks
            for item in values:
                if isinstance(item, str) and item.isupper():
                    readable = item.replace("_", " ").title()
                    formatted_items.append(f"\n  • {readable}")
                else:
                    formatted_items.append(f"\n  • {str(item)}")
            
            return f"({len(values)} items):" + "".join(formatted_items)
    
    elif structure == "numeric_index":
        # Show values based on detail level
        items = []
        
        if detail_level == "Minimal":
            # Just show range
            numeric_keys = [k for k in param_data.keys() if str(k).isdigit() and k not in ["metadata", "description"]]
            if numeric_keys:
                first_val = get_latest_value(param_data.get("1", param_data.get(1, {})))
                # Handle nested dict result
                if isinstance(first_val, dict):
                    first_val = next(iter(first_val.values())) if first_val else 0
                    
                last_key = str(max(int(k) for k in numeric_keys))
                last_val = get_latest_value(param_data.get(last_key, {}))
                # Handle nested dict result
                if isinstance(last_val, dict):
                    last_val = next(iter(last_val.values())) if last_val else 0
                    
                if unit == "currency-USD":
                    return f"1: ${first_val:,} ... {last_key}: ${last_val:,}"
                else:
                    return f"1: {first_val} ... {last_key}: {last_val}"
            return "No values"
        elif detail_level == "Summary":
            # Show first few
            for i in range(1, min(4, len(param_data) + 1)):
                if str(i) in param_data:
                    value = get_latest_value(param_data[str(i)])
                    # Handle nested dict result
                    if isinstance(value, dict):
                        value = next(iter(value.values())) if value else 0
                    if unit == "currency-USD":
                        items.append(f"{i}: ${value:,}")
                    else:
                        items.append(f"{i}: {value}")
            
            if len(param_data) > 3:
                items.append("...")
            
            return " | ".join(items)
        else:  # Full
            # Show all values
            for key in sorted(param_data.keys(), key=lambda x: int(x) if str(x).isdigit() else 999):
                if str(key).isdigit():
                    value = get_latest_value(param_data[key])
                    # Handle nested dict result
                    if isinstance(value, dict):
                        value = next(iter(value.values())) if value else 0
                    if unit == "currency-USD":
                        items.append(f"{key}: ${value:,}")
                    else:
                        items.append(f"{key}: {value}")
            
            return " | ".join(items)
    
    elif structure == "category":
        # Show all categories
        items = []
        for cat in ["SINGLE", "JOINT", "SEPARATE", "HEAD_OF_HOUSEHOLD", "SURVIVING_SPOUSE"]:
            if cat in param_data:
                value = get_latest_value(param_data[cat])
                # Handle nested dict result
                if isinstance(value, dict):
                    value = next(iter(value.values())) if value else 0
                cat_name = cat.replace("_", " ").title()
                if unit == "currency-USD":
                    items.append(f"{cat_name}: ${value:,}")
                else:
                    items.append(f"{cat_name}: {value}")
        
        return " | ".join(items) if items else "No categories found"
    
    elif structure == "brackets":
        # Show simplified bracket structure
        brackets = param_data.get("brackets", [])
        if not brackets:
            return "No brackets"
        
        items = []
        for i, bracket in enumerate(brackets[:3]):  # Show first 3 brackets
            threshold = get_latest_value(bracket.get("threshold", {}))
            amount = get_latest_value(bracket.get("amount", {}))
            
            if metadata.get("threshold_unit") == "child":
                items.append(f"{threshold} child: {amount:.1%}")
            else:
                items.append(f">{threshold}: {amount}")
        
        if len(brackets) > 3:
            items.append("...")
        
        return " | ".join(items)
    
    elif structure == "nested_3_level":
        # Show summary for complex nested structures
        all_values = []
        for level1 in param_data.values():
            if isinstance(level1, dict) and level1 != metadata:
                for level2 in level1.values():
                    if isinstance(level2, dict):
                        for level3 in level2.values():
                            if isinstance(level3, dict):
                                value = get_latest_value(level3)
                                if value is not None:
                                    all_values.append(value)
        
        if all_values:
            if unit == "currency-USD":
                return f"Range: ${min(all_values):,} - ${max(all_values):,}"
            else:
                return f"Range: {min(all_values)} - {max(all_values)}"
        
        return "Complex nested structure"
    
    else:
        return f"Unknown structure: {structure}"

def extract_dependencies_from_variable(variable_data: Dict) -> Dict[str, List[str]]:
    """
    Extract all types of dependencies from a variable's data.
    
    Returns:
        Dictionary with dependency types as keys
    """
    deps = {
        "formula": [],
        "adds": [],
        "subtracts": [],
        "parameters": [],
        "variables": [],
        "defined_for": []
    }
    
    # Formula dependencies are handled through the variables list
    # No need to add formula as a separate dependency
    
    # Get adds dependencies
    if variable_data.get("adds"):
        deps["adds"] = variable_data["adds"]
    
    # Get subtracts dependencies
    if variable_data.get("subtracts"):
        deps["subtracts"] = variable_data["subtracts"]
    
    # Don't include parameters as dependencies - they're just values to display
    # Parameters should not appear as nodes in the graph
    
    # Get variable references in formulas
    if variable_data.get("variables"):
        deps["variables"] = variable_data["variables"]
    
    # Get defined_for conditions
    if variable_data.get("defined_for"):
        deps["defined_for"] = variable_data["defined_for"]
    
    return deps

def build_dependency_graph(
    variables: Dict,
    root_variable: str,
    max_depth: int = 10,
    stop_variables: Set[str] = None,
    expand_adds_subtracts: bool = True,
    show_parameters: bool = True,
    param_detail_level: str = "Summary",
    param_date: Optional[str] = None,
    no_params_list: List[str] = None
) -> Dict:
    """
    Build a dependency graph for a given variable.
    
    Args:
        variables: Dictionary of all variables
        root_variable: The variable to start from
        max_depth: Maximum depth to traverse
        stop_variables: Set of variables to stop at
        expand_adds_subtracts: Whether to expand add/subtract operations
    
    Returns:
        Dictionary with nodes and edges for the graph
    """
    if stop_variables is None:
        stop_variables = set()
    
    nodes = {}
    edges = []
    visited = set()
    
    def clean_variable_name(name: str) -> str:
        """Clean up variable names for matching."""
        # Remove quotes and clean up
        name = name.strip().strip('"').strip("'")
        # Replace dots with underscores for parameter names
        name = name.replace(".", "_")
        return name
    
    def traverse(var_name: str, depth: int = 0, parent: Optional[str] = None, edge_type: str = "formula"):
        """Recursively traverse dependencies."""
        if depth > max_depth:
            return
        
        # Clean the variable name
        var_name = clean_variable_name(var_name)
        
        if var_name in visited:
            # Still add the edge even if visited
            if parent:
                edges.append({
                    "from": var_name,
                    "to": parent,
                    "type": edge_type
                })
            return
        
        visited.add(var_name)
        
        # Add node
        node_data = {
            "id": var_name,
            "label": var_name,
            "level": depth,
            "type": "variable"
        }
        
        # Check if this is a stop variable
        if var_name in stop_variables:
            node_data["type"] = "stop"
            nodes[var_name] = node_data
            if parent:
                edges.append({
                    "from": var_name,
                    "to": parent,
                    "type": edge_type
                })
            return
        
        # Get variable data
        var_data = variables.get(var_name, {})
        
        # Create enhanced tooltip with parameter information (using plain text for PyVis compatibility)
        tooltip_parts = []
        
        # Add variable label
        if var_data.get("label"):
            tooltip_parts.append(var_data['label'])
        else:
            tooltip_parts.append(var_name)
        
        # Add parameter information if available and enabled (and not in no_params_list)
        if show_parameters and var_data.get("parameters") and var_name not in (no_params_list or []):
            param_info = var_data["parameters"]
            if param_info:
                tooltip_parts.append("\n\nPARAMETERS:")
                for param_name, param_path in param_info.items():
                    # Load parameter data
                    param_data = load_parameter_file(param_path)
                    if param_data:
                        # Get formatted value with detail level
                        param_value = format_parameter_value(param_data, param_name, param_detail_level)
                        # Remove any HTML from the formatted value
                        param_value = param_value.replace("<br>", "\n")
                        param_label = param_data.get("metadata", {}).get("label", param_name)
                        tooltip_parts.append(f"\n• {param_label}: {param_value}")
                    else:
                        tooltip_parts.append(f"\n• {param_name}: Not found")
        
        
        node_data["title"] = "".join(tooltip_parts)
        nodes[var_name] = node_data
        
        # Add edge from dependency to parent (reversed direction)
        if parent:
            edges.append({
                "from": var_name,
                "to": parent,
                "type": edge_type
            })
        
        # Process dependencies
        all_deps = extract_dependencies_from_variable(var_data)
        
        # Process defined_for dependencies - add them as direct dependencies
        for defined_for_var in all_deps["defined_for"]:
            defined_for_var = clean_variable_name(defined_for_var)
            if defined_for_var and defined_for_var != var_name:
                # Add the defined_for variable as a direct dependency
                traverse(defined_for_var, depth + 1, var_name, "defined_for")
        
        # Process variable references in formulas
        for dep in all_deps["variables"]:
            dep = clean_variable_name(dep)
            if dep and dep != var_name:
                traverse(dep, depth + 1, var_name, "formula")
        
        # Process formula dependencies
        for dep in all_deps["formula"]:
            dep = clean_variable_name(dep)
            if dep and dep != var_name:
                traverse(dep, depth + 1, var_name, "formula")
        
        # Don't traverse parameters - they're not variables!
        # Parameters are just values to display, not nodes in the dependency graph
        
        # Process adds/subtracts if enabled
        if expand_adds_subtracts:
            for dep in all_deps["adds"]:
                dep = clean_variable_name(dep)
                if dep and dep != var_name:
                    traverse(dep, depth + 1, var_name, "adds")
            
            for dep in all_deps["subtracts"]:
                dep = clean_variable_name(dep)
                if dep and dep != var_name:
                    traverse(dep, depth + 1, var_name, "subtracts")
    
    # Start traversal
    traverse(root_variable)
    
    return {"nodes": nodes, "edges": edges}

def create_flowchart(graph_data: Dict, show_labels: bool = True, show_parameters: bool = True) -> str:
    """
    Create an interactive flowchart using pyvis.
    
    Args:
        graph_data: Dictionary with nodes and edges
        show_labels: Whether to show labels on nodes
        show_parameters: Whether to show parameter nodes
    
    Returns:
        HTML string of the network graph
    """
    net = Network(height="800px", width="100%", directed=True)
    
    # Configure hierarchical layout
    
    # Always use hierarchical tree layout
    try:
        # Try modern pyvis method first
        if hasattr(net, 'set_options'):
            net.set_options("""
            {
                "layout": {
                    "hierarchical": {
                        "enabled": true,
                        "direction": "UD",
                        "sortMethod": "directed",
                        "nodeSpacing": 180,
                        "levelSeparation": 120,
                        "treeSpacing": 150,
                        "blockShifting": true,
                        "edgeMinimization": true
                    }
                },
                "physics": {
                    "enabled": false
                }
            }
            """)
        else:
            # Fallback for older versions
            net.toggle_physics(False)
    except Exception:
        # Last resort - just disable physics
        try:
            net.toggle_physics(False)
        except:
            pass
    
    # Keep track of which nodes were actually added to the visualization
    added_nodes = set()
    
    # Add nodes
    for node_id, node_data in graph_data["nodes"].items():
        # Set node color based on type
        if node_data.get("type") == "stop":
            color = "#ff9999"  # Light red for stop variables
        elif node_data["level"] == 0:
            color = "#90EE90"  # Light green for root
        else:
            color = "#87CEEB"  # Light blue for dependencies
        
        # Prepare node attributes with better styling
        node_attrs = {
            "color": color,
            "font": {"size": 12, "face": "Arial", "color": "#333333"},
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "shape": "box",
            "margin": 8,
            "widthConstraint": {"maximum": 180},
            "heightConstraint": {"minimum": 35}
        }
        
        # Add label if enabled
        label = node_data["label"] if show_labels else ""
        
        # Add title (tooltip) if available
        title = node_data.get("title", node_data["label"])
        
        net.add_node(
            node_id,
            label=label,
            title=title,
            **node_attrs
        )
        added_nodes.add(node_id)
    
    # Add edges
    for edge in graph_data["edges"]:
        from_node = edge["from"]
        to_node = edge["to"]
        
        # Only add edge if both nodes were actually added to the visualization
        if from_node not in added_nodes or to_node not in added_nodes:
            continue
        
        # Set edge color based on type
        if edge["type"] == "adds":
            edge_color = "#00ff00"  # Green for adds
            edge_label = "+"
        elif edge["type"] == "subtracts":
            edge_color = "#ff0000"  # Red for subtracts
            edge_label = "-"
        elif edge["type"] == "defined_for":
            edge_color = "#ff9900"  # Orange for defined_for
            edge_label = "⚡"  # Lightning bolt for conditional
        elif edge["type"] == "parameter":
            edge_color = "#9900ff"  # Purple for parameters
            edge_label = "📊"
        else:
            edge_color = "#666666"  # Gray for formula/variables
            edge_label = ""
        
        net.add_edge(
            from_node,
            to_node,
            color=edge_color,
            label=edge_label,
            arrows="to",
            width=2,
            smooth={"type": "curvedCW", "roundness": 0.1},
            font={"size": 10, "color": "#444444"}
        )
    
    # Skip advanced options for compatibility - pyvis will use defaults
    
    # Generate HTML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        net.save_graph(f.name)
        with open(f.name, 'r') as html_file:
            html_content = html_file.read()
    
    return html_content

def main():
    """Main Streamlit app."""
    st.title("📊 PolicyEngine Variable Dependency Visualizer")
    st.markdown("""
    This tool generates interactive dependency flowcharts for PolicyEngine variables.
    Enter a variable name below to visualize its dependencies.
    """)
    
    # Load variables
    variables = load_variables()
    
    if not variables:
        st.stop()
    
    # Create two columns for layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("Configuration")
        
        # Variable input with search
        input_method = st.radio(
            "Choose input method:",
            ["🔍 Search from list", "⌨️ Type manually"],
            horizontal=True
        )
        
        if input_method == "🔍 Search from list":
            # Initialize session state for selected variable if not exists
            if 'selected_variable' not in st.session_state:
                st.session_state.selected_variable = ""
            
            # Create searchable selectbox with all variables
            all_variable_names = sorted(variables.keys())
            
            # Add some popular variables at the top
            popular_vars = [
                "household_net_income", "federal_income_tax", "eitc", "snap", 
                "dc_agi", "ca_income_tax", "medicaid", "ssi", "social_security"
            ]
            popular_available = [v for v in popular_vars if v in variables]
            
            # Combine popular + all others
            if popular_available:
                st.write("**Popular variables:**")
                popular_cols = st.columns(min(3, len(popular_available)))
                for i, var in enumerate(popular_available):
                    with popular_cols[i % len(popular_cols)]:
                        if st.button(var, key=f"pop_{var}"):
                            st.session_state.selected_variable = var
                
                # Use selectbox with the session state value
                variable_name = st.selectbox(
                    "Or search all variables:",
                    [""] + all_variable_names,
                    index=all_variable_names.index(st.session_state.selected_variable) + 1 if st.session_state.selected_variable in all_variable_names else 0,
                    help=f"Search among {len(all_variable_names)} PolicyEngine variables",
                    key="variable_selectbox"
                )
                
                # Update session state if selectbox changes
                if variable_name and variable_name != st.session_state.selected_variable:
                    st.session_state.selected_variable = variable_name
                elif not variable_name:
                    variable_name = st.session_state.selected_variable
            else:
                variable_name = st.selectbox(
                    "Select Variable:",
                    [""] + all_variable_names,
                    help=f"Search among {len(all_variable_names)} PolicyEngine variables"
                )
        else:
            variable_name = st.text_input(
                "Variable Name",
                placeholder="e.g., household_net_income",
                help="Enter the name of the PolicyEngine variable to visualize"
            )
        
        # Advanced options
        with st.expander("Advanced Options"):
            max_depth = st.slider(
                "Maximum Depth",
                min_value=1,
                max_value=20,
                value=10,
                help="Maximum depth to traverse in the dependency tree"
            )
            
            expand_adds_subtracts = st.checkbox(
                "Expand Adds/Subtracts",
                value=True,
                help="Show variables used in add/subtract operations"
            )
            
            show_labels = st.checkbox(
                "Show Labels",
                value=True,
                help="Display variable names on nodes"
            )
            
            show_parameters = st.checkbox(
                "Show Parameters",
                value=True,
                help="Display parameter dependencies"
            )
            
            # Parameter display options
            if show_parameters:
                st.markdown("**Parameter Display Options:**")
                
                param_detail_level = st.select_slider(
                    "Parameter Detail Level",
                    options=["Minimal", "Summary", "Full"],
                    value="Summary",
                    help="Control how much detail to show for parameter values"
                )
                
                use_latest_params = st.checkbox(
                    "Use Latest Parameter Values",
                    value=True,
                    help="Always show the most recent parameter values"
                )
                
                if not use_latest_params:
                    param_date = st.date_input(
                        "Parameter Date",
                        value=datetime.now(),
                        help="Select date for parameter values"
                    )
                else:
                    param_date = None
            else:
                param_detail_level = "Summary"
                param_date = None
            
            # Always use hierarchical tree layout
            
            # User-defined stop variables (optional)
            stop_variables_input = st.text_area(
                "Stop Variables (optional)",
                placeholder="employment_income\nself_employment_income\npension_income",
                help="Add variables to stop at if the graph is too complex. These won't expand their dependencies.",
                height=100
            )
            
            # Parse user input
            custom_stops = [v.strip() for v in stop_variables_input.split('\n') if v.strip()]
            
            # Combine with hidden default stops (DEFAULT_STOP_VARIABLES work silently in background)
            stop_variables = set(DEFAULT_STOP_VARIABLES + custom_stops)
            
            # Variables to not show parameters for (optional)
            if show_parameters:
                no_params_input = st.text_area(
                    "Don't Show Parameters For (optional)",
                    placeholder="ca_riv_share_eligible\nca_riv_share_electricity_emergency_payment",
                    help="List variables that should not display parameter values in their tooltips",
                    height=100
                )
                no_params_list = [v.strip() for v in no_params_input.split('\n') if v.strip()]
            else:
                no_params_list = []
        
        # Generate button
        generate_button = st.button("Generate Flowchart", type="primary", use_container_width=True)
        
        # Add performance warning if settings might create large graphs
        if max_depth > 15 or (expand_adds_subtracts and max_depth > 10):
            st.warning("⚠️ **Large Graph Warning:** These settings may create very large graphs. Consider:\n"
                      "- Reducing max depth to 10 or less\n" 
                      "- Adding stop variables\n"
                      "- Disabling 'Expand Adds/Subtracts' for initial exploration")
    
    with col2:
        st.header("Dependency Flowchart")
        
        # Initialize no_params_list if not defined
        if 'no_params_list' not in locals():
            no_params_list = []
            
        if generate_button and variable_name:
            # Clean the input variable name
            variable_name = variable_name.strip()
            
            # Check if variable exists
            if variable_name not in variables:
                st.error(f"Variable '{variable_name}' not found in the database.")
                st.info("Available variables (showing first 20):")
                available = list(variables.keys())[:20]
                st.code('\n'.join(available))
            else:
                with st.spinner("Building dependency graph..."):
                    # Build the graph
                    graph_data = build_dependency_graph(
                        variables,
                        variable_name,
                        max_depth=max_depth,
                        stop_variables=stop_variables,
                        expand_adds_subtracts=expand_adds_subtracts,
                        show_parameters=show_parameters,
                        param_detail_level=param_detail_level if show_parameters else "Summary",
                        param_date=param_date.strftime("%Y-%m-%d") if param_date else None,
                        no_params_list=no_params_list if show_parameters else []
                    )
                    
                    # Check graph size and warn if very large
                    num_nodes = len(graph_data['nodes'])
                    num_edges = len(graph_data['edges'])
                    
                    if num_nodes > 100:
                        st.warning(f"🐌 **Large Graph:** {num_nodes} nodes and {num_edges} edges. "
                                 f"Rendering may be slow. Consider adding more stop variables or reducing depth.")
                    elif num_nodes > 50:
                        st.info(f"📊 **Medium Graph:** {num_nodes} nodes and {num_edges} edges. This may take a moment to render.")
                    else:
                        st.success(f"✅ **Manageable Graph:** {num_nodes} nodes and {num_edges} edges")
                    
                    # Create and display the flowchart
                    html_content = create_flowchart(
                        graph_data,
                        show_labels=show_labels,
                        show_parameters=show_parameters,
                    )
                    
                    # Display the interactive graph
                    st.components.v1.html(html_content, height=800, scrolling=True)
                    
                    # Show legend
                    with st.expander("Legend"):
                        st.markdown("""
                        **Nodes:**
                        - 🟢 **Green Node**: Root variable (starting point)
                        - 🔵 **Blue Nodes**: Dependencies (contribute to parent)
                        - 🔴 **Red Nodes**: Stop variables
                        
                        **Edges (Arrows point toward calculated variable):**
                        - ➕ **Green (+)**: Added to parent variable
                        - ➖ **Red (-)**: Subtracted from parent variable
                        - ⚡ **Orange**: Conditional dependency (defined_for)
                        - 📊 **Purple**: Parameter dependency
                        - ➡️ **Gray**: Formula/variable reference
                        """)
        elif generate_button:
            st.warning("Please enter a variable name.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <small>
        Data source: <a href='https://github.com/policyengine/policyengine-us'>PolicyEngine US</a> | 
        Built with Streamlit and PyVis
        </small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()