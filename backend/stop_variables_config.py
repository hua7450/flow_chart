"""
Configuration file for stop variables in the PolicyEngine Variable Dependency Visualizer.

This file contains lists of variables that should be treated as terminal nodes in the 
dependency graph. These are typically basic demographic, geographic, or filing status
variables that don't need their dependencies expanded.

Modify these lists as needed to adjust which variables are offered as stop points.
"""

# Default stop variables that are pre-checked in the UI
DEFAULT_STOP_VARIABLES = [
    'county_str',
    'state_group_str', 
    'is_married',
    'is_child',
    'is_tax_unit_dependent',
    'is_tax_unit_head',
    'is_tax_unit_spouse',
    'monthly_age',
    'is_full_time_student',
    'tax_unit_married',
    'filing_status',
    'immigration_status',
    'employment_income',
    'self_employment_income',  
]

# Additional stop variables that are available but not pre-checked
# Users can still check these manually if needed
OPTIONAL_STOP_VARIABLES = []

# Categories for better organization (optional - for future UI improvements)
STOP_VARIABLES_BY_CATEGORY = {
    "Demographics": [
        'age',
        'is_child',
        'is_adult',
        'is_senior',
        'is_married',
        'is_pregnant'
    ],
    "Tax Unit": [
        'is_tax_unit_dependent',
        'is_tax_unit_head',
        'is_tax_unit_spouse',
        'tax_unit_married',
        'filing_status',
        'tax_unit_size'
    ],
    "Geography": [
        'county_str',
        'state_group_str',
        'state_code'
    ],
    "Student Status": [
        'is_full_time_student'
    ],
    "Immigration": [
        'immigration_status'
    ],
    "Disability": [
        'is_disabled',
        'is_blind'
    ],
    "Income": [
        'employment_income',
        'self_employment_income'
    ],
    "Household": [
        'household_size',
        'spm_unit_size'
    ],
    "Other": [
        'is_veteran',
        'year',
        'month'
    ]
}

# Common variable groups that users might want to stop at once
STOP_VARIABLE_PRESETS = {
}

# Export the main list that app.py will use
STOP_VARIABLES = DEFAULT_STOP_VARIABLES