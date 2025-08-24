#!/usr/bin/env python3
"""
Flask API backend for PolicyEngine Flowchart Visualizer
Serves PolicyEngine variable data and dependency graphs to the React frontend
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import ast
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import yaml
from datetime import datetime
import re

# Import functions from the existing app.py
from app import (
    load_variables,
    build_dependency_graph,
    load_parameter_file,
    format_parameter_value,
    detect_parameter_structure,
    get_latest_value
)
from stop_variables_config import DEFAULT_STOP_VARIABLES

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

@app.route('/api/variables', methods=['GET'])
def get_variables():
    """Get list of all available variables."""
    try:
        variables = load_variables()
        # Return a simplified list for the frontend
        variable_list = []
        for name, data in variables.items():
            variable_list.append({
                'name': name,
                'label': data.get('label', name),
                'hasParameters': bool(data.get('parameters', {}))
            })
        
        return jsonify({
            'success': True,
            'variables': variable_list,
            'total': len(variable_list)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/variable/<variable_name>', methods=['GET'])
def get_variable_details(variable_name):
    """Get detailed information about a specific variable."""
    try:
        variables = load_variables()
        if variable_name not in variables:
            return jsonify({
                'success': False,
                'error': f'Variable {variable_name} not found'
            }), 404
        
        var_data = variables[variable_name]
        
        # Load parameter values if they exist
        parameters = {}
        if var_data.get('parameters'):
            for param_name, param_path in var_data['parameters'].items():
                param_data = load_parameter_file(param_path)
                if param_data:
                    parameters[param_name] = {
                        'path': param_path,
                        'label': param_data.get('metadata', {}).get('label', param_name),
                        'value': format_parameter_value(param_data, param_name, 'Summary'),
                        'unit': param_data.get('metadata', {}).get('unit', ''),
                        'structure': detect_parameter_structure(param_data)
                    }
        
        return jsonify({
            'success': True,
            'variable': {
                'name': variable_name,
                'label': var_data.get('label', variable_name),
                'description': var_data.get('description', ''),
                'parameters': parameters,
                'adds': var_data.get('adds', []),
                'subtracts': var_data.get('subtracts', []),
                'variables': var_data.get('variables', []),
                'defined_for': var_data.get('defined_for', [])
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/graph', methods=['POST'])
def generate_graph():
    """Generate dependency graph for a variable."""
    try:
        data = request.json
        variable_name = data.get('variable')
        max_depth = data.get('maxDepth', 10)
        expand_adds_subtracts = data.get('expandAddsSubtracts', True)
        show_parameters = data.get('showParameters', True)
        param_detail_level = data.get('paramDetailLevel', 'Summary')
        param_date = data.get('paramDate')
        stop_variables = set(data.get('stopVariables', []) + DEFAULT_STOP_VARIABLES)
        no_params_list = data.get('noParamsList', [])
        
        variables = load_variables()
        
        if variable_name not in variables:
            return jsonify({
                'success': False,
                'error': f'Variable {variable_name} not found'
            }), 404
        
        # Build the dependency graph
        graph_data = build_dependency_graph(
            variables,
            variable_name,
            max_depth=max_depth,
            stop_variables=stop_variables,
            expand_adds_subtracts=expand_adds_subtracts,
            show_parameters=show_parameters,
            param_detail_level=param_detail_level,
            param_date=param_date,
            no_params_list=no_params_list
        )
        
        # Format nodes for vis-network
        nodes = []
        for node_id, node_data in graph_data['nodes'].items():
            node_type = node_data.get('type', 'variable')
            
            # Better color scheme with border and background
            if node_data['level'] == 0:
                color = {
                    'background': '#90EE90',
                    'border': '#4CAF50',
                    'highlight': {
                        'background': '#7DD87D',
                        'border': '#4CAF50'
                    }
                }
            elif node_type == 'stop':
                color = {
                    'background': '#ffb3b3',
                    'border': '#ff6666',
                    'highlight': {
                        'background': '#ff9999',
                        'border': '#ff6666'
                    }
                }
            else:
                color = {
                    'background': '#b3d9ff',
                    'border': '#66b3ff',
                    'highlight': {
                        'background': '#99ccff',
                        'border': '#66b3ff'
                    }
                }
            
            nodes.append({
                'id': node_id,
                'label': node_id if data.get('showLabels', True) else '',
                'title': node_data.get('title', node_id),
                'level': node_data['level'],
                'color': color,
                'shape': 'box',
                'font': {
                    'size': 14,
                    'color': '#333333',
                    'face': 'Arial, sans-serif',
                    'bold': node_data['level'] == 0
                },
                'borderWidth': 2,
                'borderWidthSelected': 3
            })
        
        # Format edges
        edges = []
        for edge in graph_data['edges']:
            if edge['type'] == 'adds':
                edge_color = {'color': '#00cc00', 'highlight': '#00ff00'}
            elif edge['type'] == 'subtracts':
                edge_color = {'color': '#cc0000', 'highlight': '#ff0000'}
            else:
                edge_color = {'color': '#666666', 'highlight': '#999999'}
                
            edges.append({
                'from': edge['from'],
                'to': edge['to'],
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
        
        return jsonify({
            'success': True,
            'graph': {
                'nodes': nodes,
                'edges': edges
            },
            'stats': {
                'nodeCount': len(nodes),
                'edgeCount': len(edges)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/parameter/<path:param_path>', methods=['GET'])
def get_parameter(param_path):
    """Get parameter details and values."""
    try:
        detail_level = request.args.get('detailLevel', 'Summary')
        param_date = request.args.get('date')
        
        param_data = load_parameter_file(param_path)
        if not param_data:
            return jsonify({
                'success': False,
                'error': f'Parameter {param_path} not found'
            }), 404
        
        # Get the formatted value
        param_name = param_path.split('.')[-1]
        formatted_value = format_parameter_value(param_data, param_name, detail_level)
        
        return jsonify({
            'success': True,
            'parameter': {
                'path': param_path,
                'label': param_data.get('metadata', {}).get('label', param_name),
                'description': param_data.get('description', ''),
                'value': formatted_value,
                'unit': param_data.get('metadata', {}).get('unit', ''),
                'structure': detect_parameter_structure(param_data),
                'metadata': param_data.get('metadata', {})
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search', methods=['GET'])
def search_variables():
    """Search variables by name or label."""
    try:
        query = request.args.get('q', '').lower()
        if len(query) < 2:
            return jsonify({
                'success': True,
                'results': []
            })
        
        variables = load_variables()
        results = []
        
        for name, data in variables.items():
            label = data.get('label', '').lower()
            if query in name.lower() or query in label:
                results.append({
                    'name': name,
                    'label': data.get('label', name),
                    'hasParameters': bool(data.get('parameters', {}))
                })
        
        # Sort by relevance (exact match first, then starts with, then contains)
        results.sort(key=lambda x: (
            not x['name'].lower() == query,
            not x['name'].lower().startswith(query),
            x['name'].lower()
        ))
        
        return jsonify({
            'success': True,
            'results': results[:50]  # Limit to 50 results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)