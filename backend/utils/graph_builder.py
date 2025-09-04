#!/usr/bin/env python3
"""
Graph building module for dependency visualization.
Creates network graphs from variable dependencies.
"""

from typing import Dict, List, Set, Optional, Any
from backend.parameters.parameter_handler import ParameterHandler


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
                
                # Build title/tooltip - show only label if available, otherwise show variable name
                if 'label' in var_data:
                    tooltip_text = var_data['label']
                else:
                    tooltip_text = var_name
                
                nodes[var_name] = {
                    'level': level,
                    'type': 'stop' if is_stop else 'variable',
                    'title': tooltip_text,
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
            if len(label) > 30:
                # Insert line breaks for very long variable names
                words = label.split('_')
                formatted_label = []
                current_line = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) > 25:
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
            
            nodes.append({
                'id': node_id,
                'label': label,
                'title': node_data.get('title', node_id),
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