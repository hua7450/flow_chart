# PolicyEngine Variable Extraction Rules

This document summarizes all the variable handling rules implemented for PolicyEngine-US flow chart visualization.

## Variable Reference Patterns

### 1. Direct Entity Calls
**Pattern:** `entity('variable_name', period)`
- **Entities:** `person`, `tax_unit`, `household`, `family`, `spm_unit`, `marital_unit`
- **Example:**
```python
age = person("age", period)
income = tax_unit("adjusted_gross_income", period)
```

### 2. Entity Navigation Calls
**Pattern:** `entity1.entity2('variable_name', period)`
- Allows navigation between different entity types
- **Examples:**
```python
county = person.household("county_str", period)
spm_income = person.spm_unit("spm_unit_net_income", period)
tax_unit_income = person.tax_unit("tax_unit_income", period)
```

### 3. Chained Entity Navigation
**Pattern:** `entity1.entity2.entity3('variable_name', period)`
- Multiple levels of entity navigation
- **Example:**
```python
value = person.spm_unit.household("household_variable", period)
```

### 4. Add Function Pattern
**Pattern:** `add(entity, period, ["var1", "var2"])`
- Sums multiple variables
- **Example:**
```python
total_income = add(person, period, ["employment_income", "self_employment_income"])
```

### 5. List Comprehensions in adds/subtracts
**Pattern:** `adds = ["prefix_" + i for i in LIST]`
- Dynamically generates variable lists
- **Examples:**
```python
# Simple prefix/suffix
adds = ["social_security_" + i for i in ["retirement", "disability"]]

# With string methods
adds = [i.lower() + "_income" for i in ["CA", "NY", "TX"]]
```

### 6. Variable Lists in adds/subtracts
**Pattern:** `adds = ["var1", "var2", "var3"]`
- Static list of variables to add or subtract
- **Example:**
```python
adds = ["il_liheap_base_payment", "il_liheap_crisis_assistance_amount"]
subtracts = ["tax_exempt_interest", "tax_exempt_pension"]
```

## Special Variable Attributes

### 1. defined_for Attribute
Specifies where a variable is applicable:
- **String:** `defined_for = "il_liheap_eligible"`
- **StateCode:** `defined_for = StateCode.DC`
- **List:** `defined_for = ["condition1", "condition2"]`

Creates a special dependency edge in the graph with different visualization.

### 2. Entity Types
Variables belong to specific entity types:
- `Person` - Individual level
- `TaxUnit` - Tax filing unit
- `SPMUnit` - Supplemental Poverty Measure unit
- `Household` - Household level
- `Family` - Family unit
- `MaritalUnit` - Married couple unit

### 3. Value Types
- `float` - Numeric values (often currency)
- `bool` - True/False conditions
- `int` - Whole numbers
- `Enum` - Categorical values with specific options

## Enum Variables

### Pattern Recognition
Classes inheriting from `Enum` define categorical variables:
```python
class HousingType(Enum):
    RENT = "rent"
    OWN = "own"
    OTHER = "other"

class variable_name(Variable):
    possible_values = HousingType
```

### Display Rules
- Show only descriptive values in tooltips
- Hide constant names (RENT → "rent")
- List all possible values in node tooltips

## Stop Variables

### Purpose
Prevent infinite recursion in dependency graphs by stopping expansion at certain well-known base variables.

### Default Stop Variables
Located in `stop_variables_config.py`:
- Basic demographics: `age`, `is_child`, `is_adult`
- Geographic: `state_code`, `county`
- Income sources: `employment_income`, `self_employment_income`
- Identifiers: `is_tax_unit_head`, `is_household_head`

### Behavior
- Stop variables appear with red borders in the graph
- Their dependencies are not explored further
- Can be customized per query

## Variable Extraction Rules

### What Gets Extracted
1. **Variables in formulas** - Any variable referenced in the `formula` method
2. **Variables in adds/subtracts** - Listed variables to be summed
3. **Variables from defined_for** - Condition variables for applicability
4. **Variables in add() calls** - Variables passed to the add function
5. **Variables from entity navigation** - Cross-entity variable references

### What Doesn't Get Extracted
1. **Parameter paths** - Paths starting with "gov." are parameters, not variables
2. **Python variables** - Local variables in formulas
3. **Constants** - Hardcoded values
4. **Method names** - Entity methods like `.any()`, `.all()`, `.sum()`

## Variable vs Parameter Distinction

| Type | Pattern | Example | Treatment |
|------|---------|---------|-----------|
| Variable | Simple identifier | `employment_income` | Show as graph node |
| Parameter path | Dot notation with "gov" | `gov.ssa.ssi.amount` | Show in tooltip |
| Variable list | Simple identifiers in list | `["var1", "var2"]` | Each becomes a node |
| Parameter list | Path to parameter file | `"gov.ssa.ssi.income.sources"` | Expand and show in tooltip |

## Special Handling Cases

### 1. Circular Dependencies
- Detected and prevented during graph building
- Stop variables help break potential cycles

### 2. Missing Variables
- Variables not found in the cache are skipped
- No error thrown to maintain robustness

### 3. Dynamic Variable Names
- List comprehensions are evaluated when possible
- Complex dynamic names may not be fully resolved

## Graph Visualization Rules

### Node Types and Colors
| Node Type | Color | Border | Description |
|-----------|-------|--------|-------------|
| Target | Teal | Dark Teal | The main variable being visualized |
| Normal | Light Blue | Blue | Regular dependency variables |
| Stop | Light Background | Red | Stop variables that halt expansion |
| defined_for | Light Purple | Purple | Condition variables |

### Edge Types
| Edge Type | Style | Description |
|-----------|-------|-------------|
| depends | Gray arrow | Normal variable dependency |
| adds | Green arrow | Variable added to parent |
| subtracts | Red arrow | Variable subtracted from parent |
| defined_for | Purple arrow | Applicability condition |

## Implementation Files

- **Variable Extraction:** `/backend/variables/variable_extractor.py`
- **Graph Building:** `/backend/utils/graph_builder.py`
- **Stop Variables:** `/backend/stop_variables_config.py`
- **API Endpoints:** `/backend/api.py`

## Common Patterns in PolicyEngine

### Income Aggregation
```python
adds = ["employment_income", "self_employment_income", "pension_income"]
```

### Geographic Conditions
```python
defined_for = StateCode.CA
state = person.household("state_code", period)
```

### Age-Based Logic
```python
age = person("age", period)
is_child = person("is_child", period)
```

### Benefit Calculations
```python
base_amount = person("benefit_base", period)
additional = add(person, period, ["benefit_supplement_1", "benefit_supplement_2"])
```

---

*Last Updated: September 2025*