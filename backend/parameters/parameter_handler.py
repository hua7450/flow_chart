#!/usr/bin/env python3
"""
Parameter handling module for PolicyEngine parameters.
Manages loading and formatting of parameter YAML files.
"""

import yaml
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
from datetime import datetime


class ParameterHandler:
    """Handles PolicyEngine parameter operations."""
    
    def __init__(self, base_paths: list = None):
        if base_paths is None:
            base_paths = [
                Path("../policyengine-us/policyengine_us/parameters"),
                Path("../policyengine-us/policyengine_us/data/parameters")
            ]
        self.base_paths = base_paths
    
    def load_parameter(self, param_path: str) -> Optional[Dict]:
        """Load a parameter YAML file."""
        # Convert dot notation to path
        path_parts = param_path.replace('.yaml', '').split('.')
        
        for base_path in self.base_paths:
            yaml_path = base_path / Path(*path_parts[:-1]) / f"{path_parts[-1]}.yaml"
            
            if yaml_path.exists():
                try:
                    with open(yaml_path, 'r') as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    print(f"Error loading {yaml_path}: {e}")
            else:
                # Try treating the last part as a nested key
                # e.g., gov.usda.school_meals.income.limit.REDUCED
                # where REDUCED is a key in limit.yaml
                if len(path_parts) > 1:
                    parent_yaml_path = base_path / Path(*path_parts[:-2]) / f"{path_parts[-2]}.yaml"
                    if parent_yaml_path.exists():
                        try:
                            with open(parent_yaml_path, 'r') as f:
                                parent_data = yaml.safe_load(f)
                                # Look for the nested key
                                nested_key = path_parts[-1]
                                if nested_key in parent_data:
                                    return parent_data[nested_key]
                        except Exception as e:
                            print(f"Error loading nested parameter from {parent_yaml_path}: {e}")
        
        return None
    
    def format_value(self, param_data: Dict, param_name: str, 
                    detail_level: str = "Summary", 
                    context_variable: str = None) -> str:
        """Format parameter value for display."""
        # Import the comprehensive formatter from parameter_formatter module
        from backend.utils.parameter_formatter import format_parameter_value
        
        # Use the comprehensive formatter that handles all structures
        formatted = format_parameter_value(param_data, param_name, detail_level, context_variable)
        if formatted:
            return formatted
        
        # Fallback to simple formatting for basic values
        if 'values' in param_data:
            values = param_data['values']
            
            if detail_level == "Minimal":
                # Just show the latest value without date
                latest_date, latest_value = self.get_latest_value(values)
                return str(latest_value) if latest_value is not None else "No value"
            
            elif detail_level == "Summary":
                # Show the latest value with date
                latest_date, latest_value = self.get_latest_value(values)
                if latest_value is not None:
                    return f"{latest_value} (as of {latest_date})"
                return "No value data"
            
            elif detail_level == "Full":
                # Show the 5 most recent values
                sorted_dates = sorted(values.keys(), reverse=True)[:5]
                value_strs = []
                for date in sorted_dates:
                    value_strs.append(f"{date}: {values[date]}")
                return "\n".join(value_strs) if value_strs else "No value data"
        
        return "No value data"
    
    def get_latest_value(self, values: Dict) -> Tuple[Optional[str], Any]:
        """Get the latest value from a values dictionary."""
        if not values:
            return None, None
        
        # Sort dates and get the most recent
        sorted_dates = sorted(values.keys(), reverse=True)
        latest_date = sorted_dates[0]
        latest_value = values[latest_date]
        
        return latest_date, latest_value
    
    def detect_structure(self, param_data: Dict) -> str:
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
    
    def get_value_at_date(self, param_data: Dict, target_date: str) -> Any:
        """Get parameter value at a specific date."""
        if 'values' not in param_data:
            return None
        
        values = param_data['values']
        sorted_dates = sorted(values.keys())
        
        # Find the applicable value for the target date
        applicable_value = None
        for date in sorted_dates:
            if date <= target_date:
                applicable_value = values[date]
            else:
                break
        
        return applicable_value