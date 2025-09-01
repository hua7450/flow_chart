#!/usr/bin/env python3
"""
Flask API backend for PolicyEngine Flowchart Visualizer v2
Uses modular architecture with separated concerns.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

# Import our modular components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from backend.variables.variable_extractor import VariableExtractor
from backend.parameters.parameter_handler import ParameterHandler
from backend.utils.graph_builder import GraphBuilder
from stop_variables_config import DEFAULT_STOP_VARIABLES

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Initialize handlers
variable_extractor = VariableExtractor()
parameter_handler = ParameterHandler()
graph_builder = GraphBuilder(parameter_handler)

# Cache variables (loaded once at startup)
print("Loading variables from PolicyEngine source...")
VARIABLES_CACHE = variable_extractor.load_all_variables()
print(f"Loaded {len(VARIABLES_CACHE)} variables")


@app.route('/api/variables', methods=['GET'])
def get_variables():
    """Get list of all available variables."""
    try:
        variable_list = []
        for name, data in VARIABLES_CACHE.items():
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
        if variable_name not in VARIABLES_CACHE:
            return jsonify({
                'success': False,
                'error': f'Variable {variable_name} not found'
            }), 404
        
        var_data = VARIABLES_CACHE[variable_name]
        
        # Load parameter values if they exist
        parameters = {}
        if var_data.get('parameters'):
            for param_name, param_path in var_data['parameters'].items():
                param_data = parameter_handler.load_parameter(param_path)
                if param_data:
                    parameters[param_name] = {
                        'path': param_path,
                        'label': param_data.get('metadata', {}).get('label', param_name),
                        'value': parameter_handler.format_value(param_data, param_name, 'Summary'),
                        'unit': param_data.get('metadata', {}).get('unit', ''),
                        'structure': parameter_handler.detect_structure(param_data)
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
        
        if variable_name not in VARIABLES_CACHE:
            return jsonify({
                'success': False,
                'error': f'Variable {variable_name} not found'
            }), 404
        
        # Build parameters
        max_depth = data.get('maxDepth', 10)
        expand_adds_subtracts = data.get('expandAddsSubtracts', True)
        show_parameters = data.get('showParameters', True)
        param_detail_level = data.get('paramDetailLevel', 'Summary')
        param_date = data.get('paramDate')
        stop_variables = set(data.get('stopVariables', []) + DEFAULT_STOP_VARIABLES)
        no_params_list = data.get('noParamsList', [])
        show_labels = data.get('showLabels', True)
        
        # Build the dependency graph
        graph_data = graph_builder.build_graph(
            VARIABLES_CACHE,
            variable_name,
            max_depth=max_depth,
            stop_variables=stop_variables,
            expand_adds_subtracts=expand_adds_subtracts,
            show_parameters=show_parameters,
            param_detail_level=param_detail_level,
            param_date=param_date,
            no_params_list=no_params_list
        )
        
        # Format for vis-network
        formatted_graph = graph_builder.format_for_vis_network(graph_data, show_labels)
        
        return jsonify({
            'success': True,
            'graph': formatted_graph,
            'stats': {
                'nodeCount': len(formatted_graph['nodes']),
                'edgeCount': len(formatted_graph['edges'])
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
        
        results = []
        for name, data in VARIABLES_CACHE.items():
            label = data.get('label', '').lower()
            if query in name.lower() or query in label:
                results.append({
                    'name': name,
                    'label': data.get('label', name),
                    'hasParameters': bool(data.get('parameters', {}))
                })
        
        # Sort by relevance
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
        'timestamp': datetime.now().isoformat(),
        'variables_loaded': len(VARIABLES_CACHE)
    })


if __name__ == '__main__':
    app.run(debug=True, port=5001)