#!/usr/bin/env python3
"""
Parameter formatting utilities - complete implementation from app.py
"""

from typing import Dict, Optional, Tuple, Any


def detect_parameter_structure(param_data: Dict) -> str:
    """Detect the structure type of parameter data."""
    # Skip metadata and reference fields
    data_keys = [k for k in param_data.keys() if k not in ["metadata", "description", "values", "reference"]]
    
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
    
    # Check for state-specific structure BEFORE breakdown
    # State codes list (includes DC)
    state_codes = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]
    # Check if data keys are mostly state codes
    if data_keys:
        state_key_count = sum(1 for k in data_keys if k in state_codes)
        # If more than half of the keys are state codes, it's a state structure
        if state_key_count > len(data_keys) * 0.5:
            return "state"
    
    # Check for breakdown structure or multiple parameter keys
    # If there are multiple non-metadata keys with dict values containing dates, it's a breakdown
    if data_keys:
        # Check if any of the keys have date-keyed dictionaries as values
        has_date_values = False
        for key in data_keys[:1]:  # Check first key as sample
            if isinstance(param_data[key], dict):
                # Check if it has date-like keys
                first_subkey = next(iter(param_data[key].keys())) if param_data[key] else None
                if first_subkey and (hasattr(first_subkey, 'year') or 
                                    (isinstance(first_subkey, str) and len(first_subkey) == 10 and '-' in first_subkey)):
                    has_date_values = True
                    break
        
        if has_date_values:
            return "breakdown"
    
    # Check for numeric index structure
    numeric_keys = [k for k in data_keys if str(k).isdigit()]
    if numeric_keys:
        return "numeric_index"
    
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


def format_parameter_value(param_data: Dict, param_name: str, detail_level: str = "Summary", context_variable: str = None) -> str:
    """Format a parameter value for display based on its structure - from app.py.
    
    Args:
        param_data: The parameter data dictionary
        param_name: Name of the parameter
        detail_level: Level of detail to show
        context_variable: Optional context variable name (e.g., 'dc_liheap_payment' to show DC-specific values)
    """
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
    
    elif structure == "state":
        # Handle state-specific parameters
        state_codes = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]
        
        # Try to extract state from context variable name
        target_state = None
        if context_variable:
            # Look for state code pattern in variable name (e.g., dc_liheap, ma_tanf, ca_eitc)
            var_upper = context_variable.upper()
            for state in state_codes:
                if var_upper.startswith(f"{state}_") or f"_{state}_" in var_upper:
                    target_state = state
                    break
        
        if target_state and target_state in param_data:
            # Show the specific state value
            val = get_latest_value(param_data[target_state])
            if val is not None:
                if unit == "currency-USD" and isinstance(val, (int, float)):
                    return f"${val:,.0f} ({target_state})"
                elif unit == "/1" and isinstance(val, (int, float)):
                    return f"{val:.1%} ({target_state})" if val < 1 else f"{val:.0%} ({target_state})"
                else:
                    return f"{val} ({target_state})"
        
        # Fallback: show a range of all state values
        all_values = []
        for state in param_data:
            if state not in ["metadata", "description", "reference"]:
                val = get_latest_value(param_data[state])
                if isinstance(val, (int, float)):
                    all_values.append(val)
        
        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
            if unit == "currency-USD":
                return f"Range: ${min_val:,.0f} - ${max_val:,.0f} (varies by state)"
            else:
                return f"Range: {min_val:,.0f} - {max_val:,.0f} (varies by state)"
        
        return "State-specific values"
    
    elif structure == "breakdown":
        # Handle multi-dimensional parameters with breakdown metadata
        metadata = param_data.get("metadata", {})
        unit = metadata.get("unit", "")
        
        # Collect values by dimension
        formatted_parts = []
        
        # Generically handle any structure - just iterate and format what we find
        for key in param_data:
            if key not in ["metadata", "description", "values", "reference"]:
                value_data = param_data[key]
                # Get the latest value regardless of structure
                val = get_latest_value(value_data)
                
                if val is not None:
                    # Convert key to string first in case it's numeric
                    key_label = str(key).replace('_', ' ').title()
                    
                    # Format based on unit type
                    if unit == "currency-USD" and isinstance(val, (int, float)):
                        formatted_parts.append(f"{key_label}: ${val:,.0f}")
                    elif unit == "/1" and isinstance(val, (int, float)):
                        # Format as percentage
                        formatted_parts.append(f"{key_label}: {val:.1%}" if val < 1 else f"{key_label}: {val:.0%}")
                    elif isinstance(val, (int, float)):
                        formatted_parts.append(f"{key_label}: {val:,.0f}")
                    else:
                        formatted_parts.append(f"{key_label}: {val}")
        
        if formatted_parts:
            # Show the values based on detail level
            if detail_level == "Summary":
                return ", ".join(formatted_parts[:3])  # Limit to first 3 for summary
            elif detail_level == "Full":
                # For full detail, show all values with line breaks
                return "\n".join(formatted_parts)
            else:
                # Default case
                return ", ".join(formatted_parts)
        
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