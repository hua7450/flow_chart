#!/usr/bin/env python3
"""
Extract ALL PolicyEngine data (variables + parameters) for Railway deployment.
This ensures the app works without needing the submodule in production.
"""

import json
import yaml
import sys
from pathlib import Path
from typing import Dict, Set
from datetime import date, datetime

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from backend.variables.variable_extractor import VariableExtractor
from backend.variables.enhanced_extractor import EnhancedVariableExtractor
from backend.parameters.parameter_handler import ParameterHandler

def convert_for_json(obj):
    """Recursively convert non-JSON-serializable objects."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            if isinstance(k, (date, datetime)):
                new_key = k.isoformat()
            else:
                new_key = str(k) if not isinstance(k, str) else k
            new_dict[new_key] = convert_for_json(v)
        return new_dict
    elif isinstance(obj, list):
        return [convert_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return list(convert_for_json(item) for item in obj)
    return obj

def extract_all_parameters(variables_cache: Dict) -> Dict:
    """Extract all parameters referenced by variables."""
    all_params = set()
    
    # Collect all parameter references from variables
    for var_name, var_data in variables_cache.items():
        if 'parameters' in var_data:
            params = var_data.get('parameters', [])
            if isinstance(params, list):
                all_params.update(params)
            elif isinstance(params, dict):
                all_params.update(params.keys())
    
    print(f"   Found {len(all_params)} unique parameter references")
    
    # Load each parameter
    param_handler = ParameterHandler()
    parameters_data = {}
    loaded_count = 0
    failed_params = []
    
    for param_path in all_params:
        if not param_path:  # Skip empty strings
            continue
            
        try:
            # Try to load the parameter
            param_data = param_handler.load_parameter(param_path)
            if param_data:
                parameters_data[param_path] = param_data
                loaded_count += 1
            else:
                # Try loading the YAML file directly
                yaml_paths = [
                    Path("../policyengine-us/policyengine_us/parameters") / param_path.replace('.', '/'),
                    Path("../policyengine-us/policyengine_us/data/parameters") / param_path.replace('.', '/')
                ]
                
                for base_path in yaml_paths:
                    yaml_file = base_path.with_suffix('.yaml')
                    if yaml_file.exists():
                        with open(yaml_file, 'r') as f:
                            data = yaml.safe_load(f)
                            if data:
                                parameters_data[param_path] = data
                                loaded_count += 1
                                break
                else:
                    failed_params.append(param_path)
        except Exception as e:
            # Some parameters might be dynamic or special cases
            failed_params.append(param_path)
    
    print(f"   ✓ Successfully loaded {loaded_count} parameters")
    if failed_params:
        print(f"   ⚠ Could not load {len(failed_params)} parameters (may be dynamic)")
    
    return parameters_data

def main():
    print("="*60)
    print("PolicyEngine Complete Data Extraction for Railway")
    print("="*60)
    
    # STEP 1: Extract Variables
    print("\n1. Loading variables from PolicyEngine source...")
    variable_extractor = VariableExtractor()
    enhanced_extractor = EnhancedVariableExtractor()
    
    VARIABLES_CACHE = variable_extractor.load_all_variables()
    print(f"   ✓ Loaded {len(VARIABLES_CACHE)} variables")
    
    # STEP 2: Enhance variables
    print("\n2. Enhancing variables with bracket parameters...")
    enhanced_count = 0
    for var_name, var_data in VARIABLES_CACHE.items():
        if 'parameters' in var_data and var_data['parameters']:
            file_path = var_data.get('file_path')
            if file_path:
                try:
                    enhanced_metadata = enhanced_extractor.extract_enhanced_metadata(Path(file_path), var_name)
                    if enhanced_metadata:
                        if enhanced_metadata.get('bracket_parameters'):
                            var_data['bracket_parameters'] = enhanced_metadata['bracket_parameters']
                            enhanced_count += 1
                        if enhanced_metadata.get('parameter_details'):
                            var_data['parameter_details'] = enhanced_metadata['parameter_details']
                        if enhanced_metadata.get('direct_parameters'):
                            var_data['direct_parameters'] = enhanced_metadata['direct_parameters']
                except:
                    pass
    
    print(f"   ✓ Enhanced {enhanced_count} variables with bracket parameters")
    
    # STEP 3: Extract all parameters
    print("\n3. Extracting all referenced parameters...")
    PARAMETERS_CACHE = extract_all_parameters(VARIABLES_CACHE)
    
    # STEP 4: Also scan for all YAML files to ensure we don't miss any
    print("\n4. Scanning for additional parameter files...")
    param_base_paths = [
        Path("../policyengine-us/policyengine_us/parameters"),
        Path("../policyengine-us/policyengine_us/data/parameters")
    ]
    
    additional_params = 0
    for base_path in param_base_paths:
        if base_path.exists():
            yaml_files = list(base_path.rglob("*.yaml"))
            for yaml_file in yaml_files:
                # Convert file path to parameter key
                rel_path = yaml_file.relative_to(base_path)
                param_key = str(rel_path.with_suffix('')).replace('/', '.')
                
                if param_key not in PARAMETERS_CACHE:
                    try:
                        with open(yaml_file, 'r') as f:
                            data = yaml.safe_load(f)
                            if data:
                                PARAMETERS_CACHE[param_key] = data
                                additional_params += 1
                    except:
                        pass
    
    print(f"   ✓ Found {additional_params} additional parameters")
    print(f"   Total parameters: {len(PARAMETERS_CACHE)}")
    
    # STEP 5: Create complete data package
    print("\n5. Creating complete data package...")
    complete_data = {
        'variables': convert_for_json(VARIABLES_CACHE),
        'parameters': convert_for_json(PARAMETERS_CACHE),
        'metadata': {
            'extraction_date': datetime.now().isoformat(),
            'variable_count': len(VARIABLES_CACHE),
            'parameter_count': len(PARAMETERS_CACHE),
            'version': '1.0.0'
        }
    }
    
    # STEP 6: Save complete data
    output_path = Path(__file__).parent / 'backend' / 'complete_data_cache.json'
    print(f"\n6. Saving to {output_path}...")
    
    with open(output_path, 'w') as f:
        json.dump(complete_data, f, indent=2)
    
    file_size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"   ✓ File size: {file_size_mb:.2f} MB")
    
    # STEP 7: Verify the data
    print("\n7. Verifying extracted data...")
    with open(output_path, 'r') as f:
        loaded_data = json.load(f)
    
    print(f"   ✓ Variables: {len(loaded_data['variables'])}")
    print(f"   ✓ Parameters: {len(loaded_data['parameters'])}")
    
    # Check some key items
    test_vars = ['earned_income_tax_credit', 'income_tax', 'taxable_income']
    test_params = ['gov.irs.eitc.max', 'gov.irs.standard_deduction.amount']
    
    for test_var in test_vars:
        if test_var in loaded_data['variables']:
            print(f"   ✓ Found variable: {test_var}")
            break
    
    for test_param in test_params:
        if test_param in loaded_data['parameters']:
            print(f"   ✓ Found parameter: {test_param}")
            break
    
    print("\n" + "="*60)
    print("✓ Complete extraction successful!")
    print("  Railway will now have all data needed to run your app")
    print("="*60)

if __name__ == "__main__":
    main()