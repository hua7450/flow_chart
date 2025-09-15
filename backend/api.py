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
from backend.variables.enhanced_extractor import EnhancedVariableExtractor
from backend.variables.uk_variable_extractor import UKVariableExtractor
from backend.parameters.parameter_handler import ParameterHandler
from backend.utils.graph_builder import GraphBuilder
from stop_variables_config import DEFAULT_STOP_VARIABLES

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Initialize handlers for both US and UK
variable_extractor = VariableExtractor()
enhanced_extractor = EnhancedVariableExtractor()
uk_variable_extractor = UKVariableExtractor()
parameter_handler = ParameterHandler()
graph_builder = GraphBuilder(parameter_handler)

# Cache variables for both countries (loaded once at startup)
print("Loading US variables from PolicyEngine source...")
US_VARIABLES_CACHE = variable_extractor.load_all_variables()
print(f"Loaded {len(US_VARIABLES_CACHE)} US variables")

print("Loading UK variables from PolicyEngine-UK package...")
UK_VARIABLES_CACHE = uk_variable_extractor.load_all_variables()
print(f"Loaded {len(UK_VARIABLES_CACHE)} UK variables")

# Keep VARIABLES_CACHE as US for backward compatibility
VARIABLES_CACHE = US_VARIABLES_CACHE

# Enhance specific variables with bracket parameter information
print("Enhancing variables with bracket parameters...")
from pathlib import Path
enhanced_count = 0
for var_name, var_data in VARIABLES_CACHE.items():
    # Check if this variable has parameters
    if 'parameters' in var_data and var_data['parameters']:
        file_path = var_data.get('file_path')
        if file_path:
            try:
                enhanced_metadata = enhanced_extractor.extract_enhanced_metadata(Path(file_path), var_name)
                if enhanced_metadata:
                    # Merge the enhanced metadata
                    if enhanced_metadata.get('bracket_parameters'):
                        var_data['bracket_parameters'] = enhanced_metadata['bracket_parameters']
                        enhanced_count += 1
                    if enhanced_metadata.get('parameter_details'):
                        var_data['parameter_details'] = enhanced_metadata['parameter_details']
                    if enhanced_metadata.get('direct_parameters'):
                        var_data['direct_parameters'] = enhanced_metadata['direct_parameters']
            except Exception as e:
                # Skip variables that fail enhancement
                pass

print(f"Enhanced {enhanced_count} variables with bracket parameters")

# Debug dc_liheap_payment
if 'dc_liheap_payment' in VARIABLES_CACHE:
    dc_meta = VARIABLES_CACHE['dc_liheap_payment']
    print(f"DEBUG dc_liheap_payment parameters: {dc_meta.get('parameters', {})}")
    print(f"DEBUG dc_liheap_payment variables: {dc_meta.get('variables', [])}")


@app.route('/api/variables', methods=['GET'])
def get_variables():
    """Get list of all available variables."""
    try:
        # Get country parameter (default to US for backward compatibility)
        country = request.args.get('country', 'US').upper()
        
        # Select appropriate cache
        if country == 'UK':
            cache = UK_VARIABLES_CACHE
        else:
            cache = US_VARIABLES_CACHE
        
        variable_list = []
        for name, data in cache.items():
            variable_list.append({
                'name': name,
                'label': data.get('label', name),
                'hasParameters': bool(data.get('parameters', {}))
            })
        
        return jsonify({
            'success': True,
            'variables': variable_list,
            'total': len(variable_list),
            'country': country
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
        # Get country parameter
        country = request.args.get('country', 'US').upper()
        
        # Select appropriate cache
        if country == 'UK':
            cache = UK_VARIABLES_CACHE
        else:
            cache = US_VARIABLES_CACHE
        
        if variable_name not in cache:
            return jsonify({
                'success': False,
                'error': f'Variable {variable_name} not found in {country} data'
            }), 404
        
        var_data = cache[variable_name]
        
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
        country = data.get('country', 'US').upper()
        
        # Select appropriate cache
        if country == 'UK':
            cache = UK_VARIABLES_CACHE
        else:
            cache = US_VARIABLES_CACHE
        
        if variable_name not in cache:
            return jsonify({
                'success': False,
                'error': f'Variable {variable_name} not found in {country} data'
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
            cache,
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


@app.route('/api/countries', methods=['GET'])
def get_countries():
    """Get list of available countries."""
    return jsonify({
        'success': True,
        'countries': [
            {'code': 'US', 'name': 'United States', 'variableCount': len(US_VARIABLES_CACHE)},
            {'code': 'UK', 'name': 'United Kingdom', 'variableCount': len(UK_VARIABLES_CACHE)}
        ]
    })


@app.route('/api/search', methods=['GET'])
def search_variables():
    """Search variables by name or label."""
    try:
        query = request.args.get('q', '').lower()
        country = request.args.get('country', 'US').upper()
        
        # Select appropriate cache
        if country == 'UK':
            cache = UK_VARIABLES_CACHE
        else:
            cache = US_VARIABLES_CACHE
        
        if len(query) < 2:
            return jsonify({
                'success': True,
                'results': [],
                'country': country
            })
        
        results = []
        for name, data in cache.items():
            label = data.get('label', '')
            if label is None:
                label = ''
            label = label.lower()
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
    import os
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)