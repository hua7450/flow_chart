#!/usr/bin/env python3
"""
Cached parameter handler for production deployment.
Uses pre-extracted parameter data when YAML files aren't available.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

class CachedParameterHandler:
    """Handles PolicyEngine parameters from cached data."""
    
    def __init__(self, cache_path: str = None):
        self.parameters_cache = {}
        
        if cache_path is None:
            cache_path = Path(__file__).parent.parent / 'complete_data_cache.json'
        
        # Load parameters from cache
        if Path(cache_path).exists():
            with open(cache_path, 'r') as f:
                data = json.load(f)
                self.parameters_cache = data.get('parameters', {})
                print(f"Loaded {len(self.parameters_cache)} parameters from cache")
        else:
            print(f"Warning: Cache file not found at {cache_path}")
    
    def load_parameter(self, param_path: str) -> Optional[Dict]:
        """Load a parameter from cache."""
        # Direct lookup
        if param_path in self.parameters_cache:
            return self.parameters_cache[param_path]
        
        # Try with .yaml suffix removed
        clean_path = param_path.replace('.yaml', '')
        if clean_path in self.parameters_cache:
            return self.parameters_cache[clean_path]
        
        # Try nested keys (e.g., gov.usda.school_meals.income.limit.REDUCED)
        path_parts = param_path.split('.')
        if len(path_parts) > 1:
            # Try parent path
            parent_path = '.'.join(path_parts[:-1])
            if parent_path in self.parameters_cache:
                parent_data = self.parameters_cache[parent_path]
                nested_key = path_parts[-1]
                if isinstance(parent_data, dict) and nested_key in parent_data:
                    return parent_data[nested_key]
        
        return None
    
    def format_value(self, param_data: Dict, param_name: str, 
                    detail_level: str = "Summary", 
                    context_variable: str = None) -> str:
        """Format parameter value for display - delegates to original formatter."""
        # Import the comprehensive formatter
        try:
            from utils.parameter_formatter import format_parameter_value
            formatted = format_parameter_value(param_data, param_name, detail_level, context_variable)
            if formatted:
                return formatted
        except ImportError:
            pass
        
        # Fallback to simple formatting
        if 'values' in param_data:
            values = param_data['values']
            latest_date, latest_value = self.get_latest_value(values)
            
            if detail_level == "Minimal":
                return str(latest_value) if latest_value is not None else "No value"
            elif detail_level == "Summary":
                if latest_date and latest_value is not None:
                    return f"{latest_value} (as of {latest_date})"
                return str(latest_value) if latest_value is not None else "No value"
            else:
                # Full detail
                return str(param_data)
        
        elif 'value' in param_data:
            return str(param_data['value'])
        
        return str(param_data)
    
    def get_latest_value(self, values):
        """Get the most recent value from a values dictionary."""
        if not values:
            return None, None
        
        if isinstance(values, dict):
            # Convert string dates to datetime objects for sorting
            dates = []
            for date_str in values.keys():
                try:
                    if isinstance(date_str, str):
                        # Handle ISO format dates
                        if 'T' in date_str:
                            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        else:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        dates.append((date_obj, date_str))
                except:
                    pass
            
            if dates:
                dates.sort(reverse=True)
                latest_date_str = dates[0][1]
                return latest_date_str, values[latest_date_str]
        
        return None, values