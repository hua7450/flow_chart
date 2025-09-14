# Backup Extraction Scripts

These scripts are kept as a backup solution in case Railway's git clone approach stops working.

## When to Use These Scripts

Use these extraction scripts if:
1. Railway cannot clone the PolicyEngine submodule
2. You need to deploy without submodule access
3. You want to pre-cache data for faster startup

## How to Use

### Option 1: Extract Variables Only (1.8MB)
```bash
python3 extract_variables.py
```
This creates `backend/variables_cache.json` with all variable metadata.

### Option 2: Extract Everything (6.8MB) - Recommended
```bash
python3 extract_all_data.py
```
This creates `backend/complete_data_cache.json` with both variables AND parameters.

## Deployment with Cache

If you need to use the cache approach:

1. Run extraction script locally:
   ```bash
   python3 extract_all_data.py
   ```

2. Update `backend/api.py` to use cache:
   ```python
   # Add at the top of api.py after imports
   import json
   from pathlib import Path
   
   # Check for cache file
   cache_path = Path(__file__).parent / 'complete_data_cache.json'
   if cache_path.exists():
       # Use cached data
       with open(cache_path, 'r') as f:
           data = json.load(f)
           VARIABLES_CACHE = data['variables']
       # Also update parameter_handler to use cached parameters
   ```

3. Commit cache file and push:
   ```bash
   git add backend/complete_data_cache.json
   git commit -m "Add cached data for deployment"
   git push
   ```

## Current Approach (Preferred)

The app currently uses direct git clone in `railway.toml`:
```toml
buildCommand = "git clone https://github.com/PolicyEngine/policyengine-us.git policyengine-us 2>/dev/null || true && pip install -r requirements.txt"
```

This is cleaner and always gets the latest PolicyEngine data.

## Files in This Folder

- `extract_variables.py` - Extracts only variables (smaller file)
- `extract_all_data.py` - Extracts variables + parameters (complete solution)
- `README.md` - This file