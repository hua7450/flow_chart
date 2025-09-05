# Advanced Options Guide

## Overview

The PolicyEngine Variable Dependency Visualizer provides several advanced options to customize how dependency graphs are generated and displayed. This guide explains each option and how to use them effectively.

## Configuration Options

### 1. Maximum Depth

**What it does**: Controls how many levels deep the dependency tree will traverse from your target variable.

**Range**: 1 to 20 levels

**How it works**:
- **Depth 1**: Shows only direct dependencies of the target variable
- **Depth 2**: Shows dependencies and their dependencies (grandchildren)
- **Depth 3+**: Continues expanding outward

**Example**:
```
Depth 1: household_net_income → [employment_income, benefits]
Depth 2: household_net_income → employment_income → [wages, tips]
                              → benefits → [snap, tanf]
```

**Best practices**:
- Start with depth 3-4 for initial exploration
- Use depth 1-2 for focused analysis of direct dependencies
- Use depth 5-10 for comprehensive dependency mapping
- Use depth 10-20 only for extremely deep dependency chains
- Depths above 10 may create very large graphs that impact performance
- Note: The default starting value is 10

### 2. Expand Adds/Subtracts

**What it does**: Controls whether addition and subtraction operations show individual variables or are collapsed.

**Options**:
- **Enabled (default)**: Shows each variable in add/subtract operations separately
- **Disabled**: Groups them into single "adds" or "subtracts" nodes

**Example with Enabled**:
```
gross_income → employment_income
            → self_employment_income
            → capital_gains
            → interest_income
```

**Example with Disabled**:
```
gross_income → [adds: 4 variables]
```

**When to use**:
- **Enable** when you need to see all components of calculations
- **Disable** when add/subtract lists are very long and cluttering the graph

### 3. Show Labels

**What it does**: Controls whether variable names are displayed directly on graph nodes.

**Options**:
- **Enabled**: Variable names appear on nodes
- **Disabled**: Nodes show only as circles (hover to see names)

**Best practices**:
- **Enable** for graphs with fewer nodes or when creating documentation
- **Disable** for very large graphs where labels overlap
- Always enabled for exported images

### 4. Show Parameters

**What it does**: Controls whether parameter dependencies are included in the graph.

**Options**:
- **Enabled (default)**: Shows parameters as nodes with their values
- **Disabled**: Hides all parameter nodes

**When to use**:
- **Enable** to understand complete calculation logic including thresholds and rates
- **Disable** to focus only on variable relationships

**Example impact**:
```
With Parameters: tax_calculation → income
                               → tax_rate (parameter: 0.22)
                               → standard_deduction (parameter: $13,850)

Without Parameters: tax_calculation → income
```

### 5. Parameter Detail Level

**What it does**: Controls how much information is shown for parameter values.

**Options**:
- **Minimal**: Shows only the current value
- **Summary**: Shows current value with effective date
- **Full**: Shows historical values and complete lists

**Examples**:
```
Minimal: 14580
Summary: 14580 (as of 2024-01-01)
Full:    2024-01-01: 14580
         2023-01-01: 13590
         2022-01-01: 12880
```

**See**: [Parameter Detail Levels Guide](PARAMETER_DETAIL_LEVELS.md) for comprehensive details.

### 6. Stop Variables

**What it does**: Specifies variables where the dependency traversal should stop, preventing further expansion.

**Format**: Comma-separated list of variable names

**Built-in stop variables** (pre-configured defaults):
- Basic demographics: `age`, `is_child`, `is_adult`, `person_id`
- Geographic: `state_code`, `county`, `zip_code`
- Base income sources: `employment_income`, `self_employment_income`
- Identifiers: `is_tax_unit_head`, `is_household_head`

**Customizing built-in stop variables**: 
The default stop variables can be modified by editing `/backend/stop_variables_config.py`. This file contains:
- `DEFAULT_STOP_VARIABLES`: Variables that are pre-checked in the UI
- `OPTIONAL_STOP_VARIABLES`: Additional variables available but not pre-checked
- `STOP_VARIABLES_BY_CATEGORY`: Organized groups for future UI improvements

**How to use**:
1. Enter variable names separated by commas
2. Example: `wages, social_security, pension_income`
3. The graph will show these variables but won't expand their dependencies

**When to use**:
- Prevent infinite recursion in circular dependencies
- Focus on high-level relationships
- Exclude well-understood base variables
- Reduce graph complexity

**Example**:
```
Without stop variable:
  household_income → employment_income → wages → hourly_rate
                                               → hours_worked

With "wages" as stop variable:
  household_income → employment_income → wages [STOP]
```

## Recommended Configurations

### For Initial Exploration
```
- Maximum Depth: 3
- Expand Adds/Subtracts: Enabled
- Show Labels: Enabled
- Show Parameters: Enabled
- Parameter Detail: Summary
- Stop Variables: (use defaults)
```

### For Detailed Analysis
```
- Maximum Depth: 5-6
- Expand Adds/Subtracts: Enabled
- Show Labels: Enabled
- Show Parameters: Enabled
- Parameter Detail: Full
- Stop Variables: (use defaults)
```

### For High-Level Overview
```
- Maximum Depth: 2
- Expand Adds/Subtracts: Disabled
- Show Labels: Enabled
- Show Parameters: Disabled
- Parameter Detail: Minimal
- Stop Variables: Add common variables
```

### For Large Variable Networks
```
- Maximum Depth: 4
- Expand Adds/Subtracts: Disabled
- Show Labels: Disabled (use hover)
- Show Parameters: Disabled
- Parameter Detail: Minimal
- Stop Variables: Add many base variables
```

### For Documentation/Presentation
```
- Maximum Depth: 2-3
- Expand Adds/Subtracts: Enabled
- Show Labels: Enabled
- Show Parameters: Enabled
- Parameter Detail: Summary
- Stop Variables: Add variables to focus the view
```

## Tips and Tricks

### Managing Graph Complexity

1. **Start Simple**: Begin with depth 2-3 and increase gradually
2. **Use Stop Variables**: Add variables to stop list when they make the graph too complex
3. **Toggle Parameters**: Turn off parameters initially, then enable to see specific values
4. **Adjust Incrementally**: Change one setting at a time to understand its impact

### Performance Optimization

- **Large Graphs**: Reduce depth, disable labels, use minimal parameter detail
- **Slow Loading**: Add more stop variables, disable parameter display
- **Browser Memory**: For very large variables, use depth 3 or less

### Understanding Dependencies

1. **Color Coding**:
   - **Teal**: Your target variable
   - **Light Blue**: Regular dependencies
   - **Red Border**: Stop variables
   - **Purple**: Variables with `defined_for` conditions

2. **Edge Types**:
   - **Gray Arrow**: Standard dependency
   - **Green Arrow**: Addition operation
   - **Red Arrow**: Subtraction operation
   - **Purple Arrow**: Applicability condition

### Troubleshooting Common Issues

**Graph is too cluttered**:
- Reduce maximum depth
- Add more stop variables
- Disable "Expand Adds/Subtracts"
- Turn off labels

**Can't see all dependencies**:
- Increase maximum depth
- Remove custom stop variables
- Enable "Expand Adds/Subtracts"

**Parameters overwhelming the view**:
- Set Parameter Detail to "Minimal"
- Consider disabling "Show Parameters"
- Focus on variable structure first

**Circular dependency warnings**:
- Add the circular variable to stop variables
- Reduce depth to avoid the loop

## Interactive Features

### After Generating a Graph

1. **Hover over nodes**: See detailed information about variables and parameters
2. **Click and drag nodes**: Rearrange the layout manually
3. **Zoom in/out**: Use mouse wheel or trackpad
4. **Pan**: Click and drag on empty space
5. **Select nodes**: Click to highlight a node and its direct connections

### Keyboard Shortcuts

- **Ctrl/Cmd + Mouse Wheel**: Zoom in/out
- **Spacebar + Drag**: Pan the view
- **Escape**: Deselect nodes

## Export and Sharing

### Saving Your Configuration

The application remembers your last used settings. To save a specific configuration:
1. Set up your preferred options
2. Generate a successful graph
3. The settings will persist for your next session

### Sharing Graphs

1. **Screenshot**: Use browser or OS screenshot tools
2. **Configuration**: Note your settings to recreate the same view
3. **URL Parameters**: Some settings may be shareable via URL (check current implementation)

## Examples by Use Case

### Finding Benefit Eligibility Requirements
```
Variable: snap_eligible
Maximum Depth: 3
Expand Adds/Subtracts: Yes
Show Parameters: Yes (to see income limits)
Parameter Detail: Summary
```

### Understanding Tax Calculations
```
Variable: federal_tax
Maximum Depth: 4
Expand Adds/Subtracts: Yes
Show Parameters: Yes
Parameter Detail: Full (to see tax brackets)
Stop Variables: wages, interest_income
```

### Tracing Income Sources
```
Variable: household_net_income
Maximum Depth: 5
Expand Adds/Subtracts: Yes
Show Parameters: No (focus on sources)
Stop Variables: (none - see all sources)
```

### Debugging Circular Dependencies
```
Variable: [problematic variable]
Maximum Depth: 2
Show Parameters: No
Stop Variables: [suspected circular variable]
Gradually increase depth to identify the cycle
```