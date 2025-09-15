#!/usr/bin/env python3
"""
Graph building module for dependency visualization.
Creates network graphs from variable dependencies.
"""

from typing import Dict, List, Set, Optional, Any
from parameters.parameter_handler import ParameterHandler


class GraphBuilder:
    """Builds dependency graphs for visualization."""
    
    def __init__(self, param_handler: ParameterHandler = None):
        self.param_handler = param_handler or ParameterHandler()
    
    def build_graph(self, 
                   variables: Dict,
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
                
                # Check if this is a defined_for dependency
                # It's defined_for if it's in the 'defined_for' field of the parent variable
                is_defined_for = False
                for node_name, node_data in nodes.items():
                    if 'data' in node_data:
                        defined_for_vars = node_data['data'].get('defined_for', [])
                        if isinstance(defined_for_vars, str):
                            defined_for_vars = [defined_for_vars]
                        if defined_for_vars and var_name in defined_for_vars:
                            is_defined_for = True
                            break
                
                # Build title/tooltip - show only label if available, otherwise show variable name
                if 'label' in var_data:
                    tooltip_text = var_data['label']
                else:
                    tooltip_text = var_name
                
                node_type = 'stop' if is_stop else ('defined_for' if is_defined_for else 'variable')
                
                nodes[var_name] = {
                    'level': level + (1 if is_defined_for else 0),  # Push defined_for variables down one level
                    'type': node_type,
                    'title': tooltip_text,
                    'data': var_data,
                    'param_info': [],  # Will be populated later if parameters are enabled
                    'enum_options': var_data.get('enum_options', [])  # Store enum options if available
                }
            
            # Don't expand stop variables
            if is_stop:
                return
            
            # Add dependencies
            if var_name in variables:
                var_data = variables[var_name]
                
                # Add defined_for dependencies (these are special - the variable depends on them)
                defined_for = var_data.get('defined_for', [])
                if defined_for:
                    # Normalize to list if it's a string
                    if isinstance(defined_for, str):
                        defined_for = [defined_for]
                    
                    for defined_for_var in defined_for:
                        if defined_for_var != var_name:  # Avoid self-references
                            # For defined_for, the current variable depends on the defined_for variable
                            edges.append({
                                'from': defined_for_var,
                                'to': var_name,
                                'type': 'defined_for'
                            })
                            add_dependencies(defined_for_var, level + 1)
                
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
                # BUT: If these come from a parameter list, don't add them as graph dependencies
                if expand_adds_subtracts:
                    # Check if adds comes from a parameter
                    if 'adds_from_parameter' not in var_data:
                        # Regular adds - show in graph
                        for add_var in var_data.get('adds', []):
                            if add_var != var_name:
                                edges.append({
                                    'from': add_var,
                                    'to': var_name,
                                    'type': 'adds'
                                })
                                add_dependencies(add_var, level + 1)
                    # If it's from a parameter, it will be shown in the tooltip instead
                    
                    # Check if subtracts comes from a parameter
                    if 'subtracts_from_parameter' not in var_data:
                        # Regular subtracts - show in graph
                        for sub_var in var_data.get('subtracts', []):
                            if sub_var != var_name:
                                edges.append({
                                    'from': sub_var,
                                    'to': var_name,
                                    'type': 'subtracts'
                                })
                                add_dependencies(sub_var, level + 1)
                    # If it's from a parameter, it will be shown in the tooltip instead
                
                # Load parameter values if enabled (but don't create separate nodes)
                if show_parameters and var_name not in no_params_list:
                    parameters = var_data.get('parameters', {})
                    param_info = []
                    if var_name == 'dc_liheap_payment':
                        print(f"DEBUG: dc_liheap_payment parameters = {parameters}")
                    
                    # Special case for hhs_smi: skip redundant sub-parameters
                    params_to_skip = set()
                    if var_name == 'hhs_smi':
                        # These are already shown in the household_size_adjustments parameter
                        params_to_skip = {'first_person', 'second_to_sixth_person', 'additional_person'}
                    
                    for param_name, param_path in parameters.items():
                        if param_name in params_to_skip:
                            continue  # Skip redundant parameters
                        # Try to load parameter details
                        if self.param_handler:
                            param_details = self.param_handler.load_parameter(param_path)
                            if param_details:
                                # Get the parameter label from metadata
                                param_label = param_details.get('metadata', {}).get('label', param_name)
                                # Use the parameter handler to get the formatted value, passing root variable as context
                                # This ensures state-specific parameters show the correct state value
                                formatted_value = self.param_handler.format_value(param_details, param_name, param_detail_level, start_variable)
                                if formatted_value:
                                    param_info.append({
                                        'label': param_label,
                                        'value': formatted_value
                                    })
                    
                    # Add parameter info to the node data
                    if param_info:
                        nodes[var_name]['param_info'] = param_info
        
        # Start building from the target variable
        add_dependencies(start_variable, 0)
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    def format_for_vis_network(self, graph_data: Dict, show_labels: bool = True) -> Dict:
        """Format graph data for vis-network visualization."""
        nodes = []
        edges = []
        
        # Format nodes
        for node_id, node_data in graph_data['nodes'].items():
            node_type = node_data.get('type', 'variable')
            
            # Color scheme based on node type and level
            if node_data['level'] == 0:
                # Target node - Teal accent
                color = {
                    'background': '#39C6C0',  # TEAL_ACCENT
                    'border': '#227773',      # TEAL_PRESSED
                    'highlight': {
                        'background': '#39C6C0',
                        'border': '#227773'
                    }
                }
            elif node_type == 'stop':
                # Stop node - Light background with red border
                color = {
                    'background': '#F7FAFD',  # BLUE_98
                    'border': '#b50d0d',      # DARK_RED
                    'highlight': {
                        'background': '#ffebeb',
                        'border': '#b50d0d'
                    }
                }
            elif node_type == 'parameter':
                # Parameter node - Yellow/Orange theme
                color = {
                    'background': '#FFF3CD',  # Light yellow
                    'border': '#FFA500',      # Orange
                    'highlight': {
                        'background': '#FFE5B4',
                        'border': '#FF8C00'
                    }
                }
            elif node_type == 'defined_for':
                # Defined_for node - Purple theme
                color = {
                    'background': '#E6D5F7',  # Light purple
                    'border': '#8B4B9B',      # Purple
                    'highlight': {
                        'background': '#F3EBFB',
                        'border': '#6B3B7B'
                    }
                }
            else:
                # Normal node - Blue theme
                color = {
                    'background': '#D8E6F3',  # BLUE_LIGHT
                    'border': '#2C6496',      # BLUE_PRIMARY
                    'highlight': {
                        'background': '#F7FAFD',  # BLUE_98
                        'border': '#2C6496'
                    }
                }
            
            # Format label for better display (wrap long names)
            label = node_id if show_labels else ''
            if len(label) > 40:
                # Insert line breaks for very long variable names
                words = label.split('_')
                formatted_label = []
                current_line = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) > 35:
                        if current_line:
                            formatted_label.append('_'.join(current_line))
                            current_line = [word]
                            current_length = len(word)
                    else:
                        current_line.append(word)
                        current_length += len(word) + 1
                
                if current_line:
                    formatted_label.append('_'.join(current_line))
                
                label = '\n'.join(formatted_label)
            
            # Build enhanced tooltip with parameter values and full metadata
            tooltip = node_data.get('title', node_id)
            
            # Add information about parameter-based lists
            var_data = node_data.get('data', {})
            if 'adds_from_parameter' in var_data:
                tooltip += f'\n\nADDS FROM PARAMETER: {var_data["adds_from_parameter"]}'
                adds_list = var_data.get('adds', [])
                if adds_list:
                    tooltip += '\nEXPANDS TO:'
                    for var in adds_list:
                        tooltip += f'\n• {var}'
            
            if 'subtracts_from_parameter' in var_data:
                tooltip += f'\n\nSUBTRACTS FROM PARAMETER: {var_data["subtracts_from_parameter"]}'
                subtracts_list = var_data.get('subtracts', [])
                if subtracts_list:
                    tooltip += '\nEXPANDS TO:'
                    for var in subtracts_list:
                        tooltip += f'\n• {var}'
            
            # Add parameter values from adds/subtracts
            if 'adds_parameter_values' in var_data:
                tooltip += '\n\nADDS (PARAMETER VALUES):'
                for param_path, value in var_data['adds_parameter_values'].items():
                    tooltip += f'\n• {param_path.split(".")[-1]}: {value}'
            
            if 'subtracts_parameter_values' in var_data:
                tooltip += '\n\nSUBTRACTS (PARAMETER VALUES):'
                for param_path, value in var_data['subtracts_parameter_values'].items():
                    tooltip += f'\n• {param_path.split(".")[-1]}: {value}'
            
            # Add enum options if available
            enum_options = node_data.get('enum_options', [])
            if enum_options:
                tooltip += '\n\nPOSSIBLE VALUES:'
                for option in enum_options:
                    # Show only the descriptive value, not the key
                    tooltip += f'\n• {option["value"]}'
            
            # Add direct parameter info if available
            direct_params = var_data.get('direct_parameters', {})
            if direct_params:
                tooltip += '\n\nDIRECT PARAMETERS:'
                for param_name, param_path in direct_params.items():
                    tooltip += f'\n• {param_name}: {param_path}'
                    # Add the parameter value if available
                    param_details = var_data.get('parameter_details', {}).get(param_name, {})
                    if 'value' in param_details:
                        tooltip += f' = {param_details["value"]}'
            
            # Add bracket parameter info if available
            bracket_params = var_data.get('bracket_parameters', {})
            if bracket_params:
                tooltip += '\n\nBRACKET PARAMETERS:'
                for param_name, param_path in bracket_params.items():
                    tooltip += f'\n• {param_name}: {param_path}'
                    # Add bracket details if available
                    param_details = var_data.get('parameter_details', {}).get(param_name, {})
                    if 'brackets' in param_details:
                        tooltip += '\n  Bracket Thresholds:'
                        for bracket in param_details['brackets']:
                            threshold = bracket.get('threshold', 'N/A')
                            amount = bracket.get('amount', 'N/A')
                            if amount is True:
                                amount = 'Eligible'
                            elif amount is False:
                                amount = 'Not Eligible'
                            tooltip += f'\n  - Threshold {threshold}: {amount}'
                    if 'description' in param_details:
                        tooltip += f'\n  Description: {param_details["description"]}'
            
            # Add parameter info if available (regular parameters)
            param_info = node_data.get('param_info', [])
            if param_info:
                tooltip += '\n\nPARAMETERS:'
                for param in param_info:
                    # Show parameter label and formatted value
                    tooltip += f'\n• {param["label"]}: {param["value"]}'
            
            nodes.append({
                'id': node_id,
                'label': label,
                'title': tooltip,
                'level': node_data['level'],
                'color': color,
                'shape': 'box',
                'font': {
                    'size': 16,  # Increased from 14
                    'color': '#333333',
                    'face': 'Arial, sans-serif',
                    'bold': node_data['level'] == 0,
                    'multi': True,  # Enable multi-line text
                    'align': 'center'
                },
                'borderWidth': 2,
                'borderWidthSelected': 3
            })
        
        # Format edges
        for edge in graph_data['edges']:
            if edge['type'] == 'adds':
                # Green for additions
                edge_color = {'color': '#29d40f', 'highlight': '#29d40f'}  # GREEN
                edge_title = 'Added to parent variable'
            elif edge['type'] == 'subtracts':
                # Red for subtractions
                edge_color = {'color': '#b50d0d', 'highlight': '#b50d0d'}  # DARK_RED
                edge_title = 'Subtracted from parent variable'
            else:
                # Gray for normal dependencies
                edge_color = {'color': '#808080', 'highlight': '#616161'}  # GRAY/DARK_GRAY
                edge_title = 'Variable reference'
            
            edges.append({
                'from': edge['from'],
                'to': edge['to'],
                'title': edge_title,  # Add hover label for edge
                'color': edge_color,
                'arrows': {
                    'to': {
                        'enabled': True,
                        'scaleFactor': 1.2
                    }
                },
                'width': 2,
                'smooth': {
                    'enabled': True,
                    'type': 'cubicBezier',
                    'roundness': 0.5
                }
            })
        
        return {
            'nodes': nodes,
            'edges': edges
        }