#!/usr/bin/env python3
"""
Extract all PolicyEngine variables to a JSON file for production deployment.
This preserves ALL data exactly as the runtime extractors would load it.
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from backend.variables.variable_extractor import VariableExtractor
from backend.variables.enhanced_extractor import EnhancedVariableExtractor

def convert_for_json(obj):
    """Recursively convert non-JSON-serializable objects."""
    from datetime import date, datetime
    
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        # Convert dict keys to strings if they're dates
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

def main():
    print("="*60)
    print("PolicyEngine Variable Extraction for Railway Deployment")
    print("="*60)
    
    # Initialize extractors - exactly as api.py does
    variable_extractor = VariableExtractor()
    enhanced_extractor = EnhancedVariableExtractor()
    
    # Load all variables - exactly as api.py does
    print("\n1. Loading variables from PolicyEngine source...")
    VARIABLES_CACHE = variable_extractor.load_all_variables()
    print(f"   ✓ Loaded {len(VARIABLES_CACHE)} variables")
    
    # Enhance variables - exactly as api.py does
    print("\n2. Enhancing variables with bracket parameters...")
    enhanced_count = 0
    for var_name, var_data in VARIABLES_CACHE.items():
        if 'parameters' in var_data and var_data['parameters']:
            file_path = var_data.get('file_path')
            if file_path:
                try:
                    enhanced_metadata = enhanced_extractor.extract_enhanced_metadata(Path(file_path), var_name)
                    if enhanced_metadata:
                        # Merge the enhanced metadata - exactly as api.py does
                        if enhanced_metadata.get('bracket_parameters'):
                            var_data['bracket_parameters'] = enhanced_metadata['bracket_parameters']
                            enhanced_count += 1
                        if enhanced_metadata.get('parameter_details'):
                            var_data['parameter_details'] = enhanced_metadata['parameter_details']
                        if enhanced_metadata.get('direct_parameters'):
                            var_data['direct_parameters'] = enhanced_metadata['direct_parameters']
                except Exception as e:
                    # Skip variables that fail enhancement - exactly as api.py does
                    pass
    
    print(f"   ✓ Enhanced {enhanced_count} variables with bracket parameters")
    
    # Convert sets to lists for JSON serialization
    print("\n3. Preparing data for JSON serialization...")
    json_safe_cache = convert_for_json(VARIABLES_CACHE)
    
    # Save to JSON file
    output_path = Path(__file__).parent / 'backend' / 'variables_cache.json'
    print(f"\n4. Saving to {output_path}...")
    
    with open(output_path, 'w') as f:
        json.dump(json_safe_cache, f, indent=2)
    
    file_size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"   ✓ File size: {file_size_mb:.2f} MB")
    
    # Verify the data
    print("\n5. Verifying extracted data...")
    with open(output_path, 'r') as f:
        loaded_data = json.load(f)
    
    print(f"   ✓ Successfully loaded {len(loaded_data)} variables from JSON")
    
    # Sample some variables to verify structure
    sample_vars = list(loaded_data.keys())[:5]
    print(f"\n6. Sample variables: {', '.join(sample_vars)}")
    
    # Check a complex variable if it exists
    test_vars = ['earned_income_tax_credit', 'income_tax', 'taxable_income']
    for test_var in test_vars:
        if test_var in loaded_data:
            var_data = loaded_data[test_var]
            print(f"\n   {test_var}:")
            print(f"     - Parameters: {len(var_data.get('parameters', []))} found")
            print(f"     - Variables: {len(var_data.get('variables', []))} dependencies")
            if var_data.get('bracket_parameters'):
                print(f"     - Has bracket parameters: Yes")
            break
    
    print("\n" + "="*60)
    print("✓ Extraction complete! Ready for Railway deployment.")
    print("="*60)

if __name__ == "__main__":
    main()