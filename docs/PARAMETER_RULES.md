# PolicyEngine Parameter Extraction Rules

This document summarizes all the parameter handling rules implemented for PolicyEngine-US flow chart visualization.

## Parameter Extraction Patterns

### 1. Basic Parameter Assignment
**Pattern:** `p = parameters(period).gov.states.xxx`
- Followed by usage like `p.max`, `p.min`, `p.rate`
- **Example:** `il_liheap_base_payment.py`
```python
p = parameters(period).gov.states.il.dceo.liheap.payment.base_amount
capped_heating_expenses = min_(heating_expenses, p.max)
```

### 2. Direct Parameter Access
**Pattern:** `limit = parameters(period).gov.usda.school_meals.income.limit.REDUCED`
- Direct assignment without intermediate variable
- **Example:** `meets_wic_income_test.py`
```python
limit = parameters(period).gov.usda.school_meals.income.limit.REDUCED
```

### 3. Nested Parameter Access
**Pattern:** `p.entry.fpg_limit.preschool`
- Multiple levels of nesting from base parameter path
- **Example:** `nc_scca_fpg_rate.py`
```python
p = parameters(period).gov.states.nc.ncdhhs.scca
return where(has_preschool_or_special_needs,
            p.entry.fpg_limit.preschool,
            p.entry.fpg_limit.school_age)
```

### 4. Bracket Parameters with .calc()
**Pattern:** `p = parameters(period).gov.states.ma...` then `p.calc(age)`
- Used for age/threshold calculations
- Display as brackets with eligibility ranges
- **Example:** `ma_mbta_income_eligible_reduced_fare_eligible.py`
```python
p = parameters(period).gov.states.ma.dot.mbta.income_eligible_reduced_fares.age_threshold
return p.calc(age)
```

### 5. Subscripted Parameter Access
**Pattern:** `p_fpg.first_person[state_group]`
- Parameters accessed using variable values as keys
- Common with state-specific or group-specific parameters
- **Example:** `spm_unit_fpg.py`
```python
p_fpg = parameters(period).gov.hhs.fpg
p1 = p_fpg.first_person[state_group]  # state_group is a variable
pn = p_fpg.additional_person[state_group]
```

### 6. Parameter Paths in adds/subtracts

#### 6a. Variable Lists from Parameters
**Pattern:** `adds = "gov.ssa.ssi.income.sources.earned"`
- Loads a list of variables from parameter file
- Display expanded list in tooltip
- **Examples:** `ssi_earned_income.py`, `il_aabd_gross_earned_income.py`

#### 6b. Single Parameter Values
**Pattern:** `adds = ["gov.states.il.dceo.liheap.payment.crisis_amount.max"]`
- References parameter values, not variables
- Display value in tooltip (e.g., "$1,500")
- **Example:** `il_liheap_crisis_assistance_amount.py`

## Parameter Consolidation Rules

Smart heuristics without hardcoding:
- **Keep separate:** 1-4 sub-parameters (like max/min, utilities)
- **Keep separate:** Short parameter names (≤10 chars) 
- **Consolidate:** 5+ long parameter names to base parameter

## Entity Navigation Patterns

Extract variables from all entity navigation patterns:
- `person('variable_name')`
- `person.household('variable_name')`
- `spm_unit.household('variable_name')`
- `tax_unit.household('variable_name')`
- Any entity-to-entity navigation
- Chained patterns like `person.spm_unit.household('variable_name')`

## Display Rules in Tooltips

| Parameter Type | Display Format | Example |
|---------------|----------------|---------|
| Regular parameters | PARAMETERS section with values | `Illinois LIHEAP maximum benefit: $2,075` |
| Bracket parameters | Age thresholds with eligibility | `Age 0: Not Eligible, Age 18: Eligible` |
| Parameter lists | "ADDS FROM PARAMETER" with expansion | Shows list of variables |
| Parameter values | "ADDS (PARAMETER VALUES)" with amounts | `max: $1,500` |
| Direct parameters | Show with their values inline | `REDUCED: 185%` |

## Other Important Rules

### Enum Display
- Show only descriptive values, not constant names
- Example: Show "Infant and Toddler" not "INFANT_AND_TODDLER"

### Stop Variables
- Built-in list prevents infinite recursion
- Variables in this list don't expand their dependencies
- Located in `stop_variables_config.py`

### Parameter vs Variable Detection
- **Parameter paths:** Contain dots and start with "gov"
- **Variable names:** Simple identifiers with underscores
- List items starting with "gov." are treated as parameter paths

## Implementation Files

- **Variable Extraction:** `/backend/variables/variable_extractor.py`
- **Enhanced Extraction:** `/backend/variables/enhanced_extractor.py`
- **Graph Building:** `/backend/utils/graph_builder.py`
- **Parameter Handling:** `/backend/parameters/parameter_handler.py`
- **Stop Variables:** `/backend/stop_variables_config.py`

---

*Last Updated: September 2025*