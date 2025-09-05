#!/usr/bin/env python3
"""
Parameter formatting utilities - complete implementation from app.py
"""

from typing import Dict, Optional, Tuple, Any


def detect_parameter_structure(param_data: Dict) -> str:
    """Detect the structure type of parameter data."""
    # Skip metadata
    data_keys = [k for k in param_data.keys() if k not in ["metadata", "description", "values"]]
    
    # Check if values contain lists (need to check this before simple)
    if "values" in param_data:
        sample_value = get_latest_value(param_data["values"])
        if isinstance(sample_value, list):
            return "list"
    
    # Check for simple value structure
    if "values" in param_data and not data_keys:
        return "simple"
    
    # Check for category structure (SINGLE, JOINT, etc.)
    categories = ["SINGLE", "JOINT", "SEPARATE", "HEAD_OF_HOUSEHOLD", "SURVIVING_SPOUSE", "WIDOW", "WIDOWER"]
    if any(cat in param_data for cat in categories):
        return "category"
    
    # Check for housing type structure (MULTI_FAMILY, SINGLE_FAMILY)
    housing_types = ["MULTI_FAMILY", "SINGLE_FAMILY"]
    if any(ht in param_data for ht in housing_types):
        return "housing_brackets"
    
    # Check for breakdown structure (like fpg with first_person/additional_person)
    # These have metadata.breakdown field and multiple top-level keys
    if "metadata" in param_data and "breakdown" in param_data.get("metadata", {}):
        # Has breakdown metadata - this is a multi-dimensional parameter
        return "breakdown"
    
    # Check for numeric index structure
    numeric_keys = [k for k in data_keys if str(k).isdigit()]
    if numeric_keys:
        return "numeric_index"
    
    # Check for state-specific structure
    state_codes = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]
    if any(state in param_data for state in state_codes):
        return "state"
    
    # Check for bracket structure
    if any(k for k in data_keys if "bracket" in str(k).lower()):
        return "brackets"
    
    return "unknown"


def get_latest_value(value_data: Any) -> Any:
    """Get the latest value from various data structures."""
    if not value_data:
        return None
    
    # If it's already a simple value, return it
    if not isinstance(value_data, dict):
        return value_data
    
    # Find keys that look like dates
    date_keys = []
    for key in value_data.keys():
        # Check if this is a datetime object
        if hasattr(key, 'year'):
            date_keys.append(key)
        # Check if this looks like a date string (YYYY-MM-DD format)
        elif isinstance(key, str) and len(key) == 10 and key[4] == "-" and key[7] == "-":
            try:
                year, month, day = key.split("-")
                if year.isdigit() and month.isdigit() and day.isdigit():
                    date_keys.append(key)
            except:
                pass
    
    if date_keys:
        # Sort dates and get the latest
        date_keys.sort()
        return value_data[date_keys[-1]]
    
    return value_data


def format_parameter_value(param_data: Dict, param_name: str, detail_level: str = "Summary") -> str:
    """Format a parameter value for display based on its structure - from app.py."""
    if not param_data:
        return None
    
    structure = detect_parameter_structure(param_data)
    metadata = param_data.get("metadata", {})
    unit = metadata.get("unit", "")
    
    if structure == "simple":
        value = get_latest_value(param_data.get("values", {}))
        if isinstance(value, dict):
            # Still has nested structure, get the actual value
            value = next(iter(value.values())) if value else 0
        
        if unit == "currency-USD":
            try:
                return f"${float(value):,.0f}"
            except:
                return str(value)
        elif unit == "/1":
            if isinstance(value, (int, float)):
                return f"{value:.1%}" if value < 1 else f"{value:.0%}"
            else:
                return str(value)
        else:
            return str(value)
    
    elif structure == "list":
        values = get_latest_value(param_data.get("values", {}))
        if not values:
            return "Empty list"
        
        # Format list items
        formatted_items = []
        
        # Check if this is a list of variable names
        is_variable_list = all(isinstance(item, str) and "_" in item and not item.isupper() for item in values[:3] if values)
        
        if detail_level == "Summary":
            # Show items as bullet points
            for item in values[:10]:  # Limit to first 10
                if isinstance(item, str):
                    # Keep the item as-is, don't transform case
                    formatted_items.append(item)
                else:
                    formatted_items.append(str(item))
            
            # Always show as bullet points for better readability
            result = "\n  - " + "\n  - ".join(formatted_items)
            if len(values) > 10:
                result += f"\n  ... and {len(values) - 10} more"
            return result
        else:  # Full
            for item in values:
                if isinstance(item, str) and item.isupper():
                    readable = item.replace("_", " ").title()
                    formatted_items.append(f"\n  • {readable}")
                else:
                    formatted_items.append(f"\n  • {str(item)}")
            
            return f"({len(values)} items):" + "".join(formatted_items[:20])  # Limit for display
    
    elif structure == "breakdown":
        # Handle multi-dimensional parameters with breakdown metadata
        # Example: fpg has first_person and additional_person, each with state groups
        metadata = param_data.get("metadata", {})
        unit = metadata.get("unit", "")
        
        
        # Collect values by dimension
        formatted_parts = []
        
        # For FPG, show CONTIGUOUS_US values as the main example
        for key in param_data:
            if key not in ["metadata", "description"]:
                dimension_data = param_data[key]
                if isinstance(dimension_data, dict):
                    # Look for CONTIGUOUS_US first as the primary example
                    if "CONTIGUOUS_US" in dimension_data:
                        val = get_latest_value(dimension_data["CONTIGUOUS_US"])
                        if isinstance(val, (int, float)) and val > 0:
                            if unit == "currency-USD":
                                formatted_parts.append(f"{key.replace('_', ' ').title()}: ${val:,.0f}")
                            else:
                                formatted_parts.append(f"{key.replace('_', ' ').title()}: {val:,.0f}")
        
        if formatted_parts:
            # Show the primary values clearly
            if detail_level == "Summary":
                # Only show CONTIGUOUS_US values in Summary
                result = "Contiguous US: "
                result += ", ".join(formatted_parts)
                return result
            
            elif detail_level == "Full":
                # Show more detailed breakdown for Full level
                result_lines = []
                
                # Group by state
                state_data = {}
                for key in param_data:
                    if key not in ["metadata", "description"]:
                        dimension_data = param_data[key]
                        if isinstance(dimension_data, dict):
                            for state, state_val_data in dimension_data.items():
                                if state not in ["GU", "PR", "VI"]:  # Skip territories with 0 values
                                    if state not in state_data:
                                        state_data[state] = {}
                                    val = get_latest_value(state_val_data)
                                    if isinstance(val, (int, float)) and val > 0:
                                        state_data[state][key] = val
                
                # Format by state
                for state in ["CONTIGUOUS_US", "AK", "HI"]:  # Show in this order
                    if state in state_data:
                        state_label = state.replace("_", " ").replace("CONTIGUOUS US", "Contiguous US")
                        result_lines.append(f"{state_label}:")
                        for dim, val in state_data[state].items():
                            dim_label = dim.replace('_', ' ').title()
                            if unit == "currency-USD":
                                result_lines.append(f"  • {dim_label}: ${val:,.0f}")
                            else:
                                result_lines.append(f"  • {dim_label}: {val:,.0f}")
                
                return "\n".join(result_lines)
        
        return "Complex parameter structure"
    
    elif structure == "housing_brackets":
        # Special handling for DC LIHEAP electricity/gas parameters with housing type structure
        all_values = []
        
        # Extract all numeric values from the nested structure
        for housing_type in ["MULTI_FAMILY", "SINGLE_FAMILY"]:
            if housing_type in param_data:
                housing_data = param_data[housing_type]
                for income_level, income_data in housing_data.items():
                    if isinstance(income_data, dict):
                        for size, size_data in income_data.items():
                            if isinstance(size_data, dict):
                                val = get_latest_value(size_data)
                                if isinstance(val, (int, float)):
                                    all_values.append(val)
        
        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
            
            if detail_level == "Summary":
                # Just show the range
                if unit == "currency-USD":
                    return f"Range: ${min_val:,.0f} - ${max_val:,.0f}"
                else:
                    return f"Range: {min_val} - {max_val}"
            
            elif detail_level == "Full":
                # Show breakdown by housing type and income level
                result_lines = []
                
                for housing_type in ["MULTI_FAMILY", "SINGLE_FAMILY"]:
                    if housing_type in param_data:
                        housing_label = housing_type.replace("_", " ").title()
                        result_lines.append(f"{housing_label}:")
                        
                        housing_data = param_data[housing_type]
                        # Show a sample of income levels
                        for income_level in sorted(list(housing_data.keys()))[:2]:  # Show first 2 income levels
                            income_data = housing_data[income_level]
                            if isinstance(income_data, dict):
                                # Get range for this income level
                                level_values = []
                                for size, size_data in income_data.items():
                                    if isinstance(size_data, dict):
                                        val = get_latest_value(size_data)
                                        if isinstance(val, (int, float)):
                                            level_values.append(val)
                                
                                if level_values:
                                    level_min = min(level_values)
                                    level_max = max(level_values)
                                    if unit == "currency-USD":
                                        result_lines.append(f"  • Income Level {income_level}: ${level_min:,.0f} - ${level_max:,.0f}")
                                    else:
                                        result_lines.append(f"  • Income Level {income_level}: {level_min} - {level_max}")
                
                if result_lines:
                    result_lines.append(f"Overall Range: ${min_val:,.0f} - ${max_val:,.0f}")
                    return "\n".join(result_lines)
                else:
                    # Fallback to range if no detailed data
                    if unit == "currency-USD":
                        return f"Range: ${min_val:,.0f} - ${max_val:,.0f}"
                    else:
                        return f"Range: {min_val} - {max_val}"
        
        return "No values available"
    
    elif structure == "numeric_index" or structure == "brackets":
        # For complex structures like electricity/gas with brackets, show range
        items = []
        
        # Check if this has bracket structure (electricity, gas payments)
        has_brackets = 'metadata' in param_data and 'breakdown' in param_data.get('metadata', {})
        
        if has_brackets and detail_level in ["Summary", "Full"]:
            # Show as range for bracket structures
            all_values = []
            # Collect all numeric values from the structure
            def extract_values(data, values_list):
                if isinstance(data, dict):
                    for k, v in data.items():
                        if k not in ['metadata', 'description']:
                            if isinstance(v, dict) and 'values' in v:
                                val = get_latest_value(v['values'])
                                if isinstance(val, (int, float)):
                                    values_list.append(val)
                            else:
                                extract_values(v, values_list)
                elif isinstance(data, (int, float)):
                    values_list.append(data)
            
            extract_values(param_data, all_values)
            
            if all_values:
                min_val = min(all_values)
                max_val = max(all_values)
                if unit == "currency-USD":
                    return f"Range: ${min_val:,.0f} - ${max_val:,.0f}"
                else:
                    return f"Range: {min_val} - {max_val}"
        
        if detail_level == "Summary":
            # Show first few
            for i in range(1, min(4, 10)):
                if str(i) in param_data:
                    value = get_latest_value(param_data[str(i)])
                    if isinstance(value, dict):
                        value = next(iter(value.values())) if value else 0
                    if unit == "currency-USD":
                        items.append(f"{i}: ${value:,.0f}")
                    else:
                        items.append(f"{i}: {value}")
            
            if len(items) > 3:
                items = items[:3] + ["..."]
            
            return " | ".join(items)
        else:  # Full
            # Show more values
            for key in sorted(param_data.keys(), key=lambda x: int(x) if str(x).isdigit() else 999)[:10]:
                if str(key).isdigit():
                    value = get_latest_value(param_data[key])
                    if isinstance(value, dict):
                        value = next(iter(value.values())) if value else 0
                    if unit == "currency-USD":
                        items.append(f"{key}: ${value:,.0f}")
                    else:
                        items.append(f"{key}: {value}")
            
            return " | ".join(items)
    
    # Default fallback
    if "values" in param_data:
        value = get_latest_value(param_data["values"])
        if value is not None:
            if unit == "currency-USD" and isinstance(value, (int, float)):
                return f"${value:,.0f}"
            return str(value)
    
    return None