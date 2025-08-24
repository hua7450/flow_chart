#!/usr/bin/env python3
"""
Fetch all variables from the PolicyEngine US repository and save them to a JSON file.
This script downloads the repository as a zip file to avoid API rate limits.
"""

import json
import requests
from typing import Dict, Optional
from pathlib import Path
import zipfile
import io
import re
import os
import tempfile
import shutil

def download_repo_zip(owner: str, repo: str, branch: str = "master") -> bytes:
    """
    Download the repository as a zip file.
    
    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name
    
    Returns:
        Zip file content as bytes
    """
    url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
    
    print(f"Downloading repository from {url}...")
    response = requests.get(url, stream=True)
    
    if response.status_code != 200:
        raise Exception(f"Failed to download repository: {response.status_code}")
    
    # Download in chunks to show progress
    chunks = []
    total_size = 0
    for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
        chunks.append(chunk)
        total_size += len(chunk)
        print(f"Downloaded {total_size / (1024*1024):.1f} MB", end='\r')
    
    print(f"\nTotal downloaded: {total_size / (1024*1024):.1f} MB")
    return b''.join(chunks)

def parse_variable_file(content: str, file_path: str) -> Optional[Dict]:
    """
    Parse a Python variable definition file to extract metadata.
    
    Args:
        content: File content
        file_path: Path to the file for reference
    
    Returns:
        Dictionary with variable metadata
    """
    variable_data = {
        "file_path": file_path,
        "formula": None,
        "adds": [],
        "subtracts": [],
        "parameters": [],
        "variables": [],  # Variables referenced in formula
        "defined_for": [],  # Variables in defined_for conditions
        "description": None,
        "label": None,
        "unit": None
    }
    
    try:
        lines = content.split('\n')
        in_class = False
        in_metadata = False
        
        for i, line in enumerate(lines):
            # Check if we're entering a class definition
            if line.strip().startswith('class ') and '(Variable)' in line:
                in_class = True
                in_metadata = True
                continue
            
            if in_class:
                # Look for metadata attributes
                stripped = line.strip()
                
                # Extract description
                if 'description =' in line:
                    match = re.search(r'description\s*=\s*["\'](.+?)["\']', line)
                    if match:
                        variable_data["description"] = match.group(1)
                
                # Extract label
                if 'label =' in line:
                    match = re.search(r'label\s*=\s*["\'](.+?)["\']', line)
                    if match:
                        variable_data["label"] = match.group(1)
                
                # Extract unit
                if 'unit =' in line:
                    match = re.search(r'unit\s*=\s*["\'](.+?)["\']', line)
                    if match:
                        variable_data["unit"] = match.group(1)
                    # Handle unit = USD or other constants
                    elif not line.strip().startswith('#'):
                        match = re.search(r'unit\s*=\s*(\w+)', line)
                        if match:
                            variable_data["unit"] = match.group(1)
                
                # Look for defined_for conditions
                if 'defined_for =' in line:
                    # Extract the condition - could be a variable reference
                    # Examples: defined_for = "ca_riv_share_eligible"
                    #          defined_for = StateCode.CA
                    match = re.search(r'defined_for\s*=\s*["\']([^"\']+)["\']', line)
                    if match:
                        defined_for_var = match.group(1)
                        if defined_for_var and defined_for_var not in variable_data["defined_for"]:
                            variable_data["defined_for"].append(defined_for_var)
                
                # Look for class-level adds (not in formula)
                if in_metadata and 'adds =' in line:
                    # Parse adds list - handle both single line and multi-line
                    if '[' in line and ']' in line:
                        # Single line list
                        match = re.search(r'adds\s*=\s*\[([^\]]+)\]', line)
                        if match:
                            adds_str = match.group(1)
                            adds = [a.strip().strip('"').strip("'") for a in adds_str.split(',') if a.strip()]
                            variable_data["adds"] = adds
                    elif '[' in line:
                        # Multi-line list - collect lines until closing ]
                        adds = []
                        start_idx = line.find('[')
                        remainder = line[start_idx+1:].strip()
                        if remainder and remainder != ']':
                            # Process first line
                            items = remainder.split(',')
                            adds.extend([a.strip().strip('"').strip("'") for a in items if a.strip()])
                        # Look ahead for more lines
                        for k in range(i+1, min(i+20, len(lines))):
                            next_line = lines[k]
                            if ']' in next_line:
                                # Last line
                                end_idx = next_line.find(']')
                                if end_idx > 0:
                                    items = next_line[:end_idx].split(',')
                                    adds.extend([a.strip().strip('"').strip("'") for a in items if a.strip()])
                                break
                            else:
                                # Middle lines
                                items = next_line.strip().split(',')
                                adds.extend([a.strip().strip('"').strip("'") for a in items if a.strip()])
                        variable_data["adds"] = adds
                
                # Look for class-level subtracts (not in formula)
                if in_metadata and 'subtracts =' in line:
                    # Parse subtracts list - handle both single line and multi-line
                    if '[' in line and ']' in line:
                        # Single line list
                        match = re.search(r'subtracts\s*=\s*\[([^\]]+)\]', line)
                        if match:
                            subtracts_str = match.group(1)
                            subtracts = [s.strip().strip('"').strip("'") for s in subtracts_str.split(',') if s.strip()]
                            variable_data["subtracts"] = subtracts
                    elif '[' in line:
                        # Multi-line list - collect lines until closing ]
                        subtracts = []
                        start_idx = line.find('[')
                        remainder = line[start_idx+1:].strip()
                        if remainder and remainder != ']':
                            # Process first line
                            items = remainder.split(',')
                            subtracts.extend([s.strip().strip('"').strip("'") for s in items if s.strip()])
                        # Look ahead for more lines
                        for k in range(i+1, min(i+20, len(lines))):
                            next_line = lines[k]
                            if ']' in next_line:
                                # Last line
                                end_idx = next_line.find(']')
                                if end_idx > 0:
                                    items = next_line[:end_idx].split(',')
                                    subtracts.extend([s.strip().strip('"').strip("'") for s in items if s.strip()])
                                break
                            else:
                                # Middle lines
                                items = next_line.strip().split(',')
                                subtracts.extend([s.strip().strip('"').strip("'") for s in items if s.strip()])
                        variable_data["subtracts"] = subtracts
                
                # Look for formula method
                if 'def formula(' in line:
                    in_metadata = False
                    # Look ahead for formula content
                    for j in range(i+1, min(i+50, len(lines))):
                        formula_line = lines[j]
                        
                        # Check for imports from formulas
                        if 'from ' in formula_line and 'formulas.' in formula_line:
                            match = re.search(r'from\s+[\w\.]+formulas\.[\w\.]+\s+import\s+(\w+)', formula_line)
                            if match:
                                variable_data["formula"] = match.group(1)
                        
                        # Check for direct formula references
                        if 'formulas.' in formula_line:
                            match = re.search(r'formulas\.([\w\.]+)', formula_line)
                            if match:
                                formula_name = match.group(1).split('.')[-1]
                                variable_data["formula"] = formula_name
                        
                        # Check for adds
                        if '.adds =' in formula_line or 'adds =' in formula_line:
                            match = re.search(r'adds\s*=\s*\[([^\]]+)\]', formula_line)
                            if match:
                                adds_str = match.group(1)
                                adds = [a.strip().strip('"').strip("'") for a in adds_str.split(',') if a.strip()]
                                variable_data["adds"] = adds
                        
                        # Check for subtracts
                        if '.subtracts =' in formula_line or 'subtracts =' in formula_line:
                            match = re.search(r'subtracts\s*=\s*\[([^\]]+)\]', formula_line)
                            if match:
                                subtracts_str = match.group(1)
                                subtracts = [s.strip().strip('"').strip("'") for s in subtracts_str.split(',') if s.strip()]
                                variable_data["subtracts"] = subtracts
                        
                        # Check for variable references in formula
                        # Look for patterns like: person("variable_name", period)
                        # or tax_unit("variable_name", period)
                        # or household("variable_name", period)
                        # Handle both single-line and multi-line calls
                        var_refs = re.findall(r'(?:person|tax_unit|household|spm_unit|family)\s*\(\s*["\']([^"\']+)["\']', formula_line)
                        for var_ref in var_refs:
                            if var_ref and var_ref not in variable_data["variables"]:
                                variable_data["variables"].append(var_ref)
                        
                        # Also look for direct variable calls like tax_unit.sum(person("var", period))
                        var_refs2 = re.findall(r'\.sum\(person\(["\']([^"\']+)["\']', formula_line)
                        for var_ref in var_refs2:
                            if var_ref and var_ref not in variable_data["variables"]:
                                variable_data["variables"].append(var_ref)
                        
                        # Check for parameter references
                        # First check if parameters(period) is assigned to a variable
                        if 'parameters(period)' in formula_line or 'parameters(year)' in formula_line:
                            # Look for pattern like: p = parameters(period).gov.states
                            match = re.search(r'(\w+)\s*=\s*parameters\([^)]+\)([\w\.]*)', formula_line)
                            if match:
                                param_var = match.group(1)  # e.g., 'p'
                                param_path = match.group(2).strip('.')  # e.g., 'gov.states'
                                
                                # Now look for uses of this variable in subsequent lines
                                for k in range(j, min(j+30, len(lines))):
                                    check_line = lines[k]
                                    # Look for patterns like p.dc.tax.income.rates
                                    if param_var in check_line:
                                        # Find all occurrences of param_var.path
                                        param_uses = re.findall(rf'{param_var}\.([\w\.]+)', check_line)
                                        for use in param_uses:
                                            # Combine the base path with the usage path
                                            if param_path:
                                                full_path = f"{param_path}.{use}"
                                            else:
                                                full_path = use
                                            # Clean up and add to parameters
                                            full_path = full_path.strip('(').strip(')')
                                            if full_path and full_path not in variable_data["parameters"]:
                                                variable_data["parameters"].append(full_path)
                        
                        # Also check for direct parameter access patterns
                        param_matches = re.findall(r'parameters\.([\w\.]+)|parameters\(["\']([^"\']+)["\']\)', formula_line)
                        for match_groups in param_matches:
                            param = match_groups[0] or match_groups[1]
                            if param and param not in variable_data["parameters"]:
                                variable_data["parameters"].append(param)
                        
                        # Stop if we reach the next method
                        if formula_line.strip().startswith('def ') and 'def formula(' not in formula_line:
                            break
        
        return variable_data
        
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None

def main():
    """
    Main function to fetch all variables and save to JSON.
    """
    owner = "policyengine"
    repo = "policyengine-us"
    branch = "master"
    
    # Download the repository as a zip file
    zip_content = download_repo_zip(owner, repo, branch)
    
    # Create a temporary directory to extract the zip
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the zip file
        print("Extracting repository contents...")
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
            zip_file.extractall(temp_dir)
        
        # Find the variables directory
        repo_root = Path(temp_dir) / f"{repo}-{branch}"
        variables_dir = repo_root / "policyengine_us" / "variables"
        
        if not variables_dir.exists():
            raise Exception(f"Variables directory not found at {variables_dir}")
        
        # Find all Python files in the variables directory
        variable_files = list(variables_dir.rglob("*.py"))
        # Exclude __init__.py files
        variable_files = [f for f in variable_files if f.name != "__init__.py"]
        
        print(f"Found {len(variable_files)} variable files")
        
        # Parse each variable file
        variables = {}
        
        for i, file_path in enumerate(variable_files):
            # Extract variable name from the file name
            variable_name = file_path.stem
            
            # Get the relative path for display
            relative_path = file_path.relative_to(repo_root)
            
            print(f"[{i+1}/{len(variable_files)}] Processing {variable_name}...")
            
            try:
                # Read the file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse the variable file
                variable_data = parse_variable_file(content, str(relative_path))
                
                if variable_data:
                    variables[variable_name] = variable_data
                    
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    # Save to JSON file
    output_file = "variables.json"
    with open(output_file, 'w') as f:
        json.dump(variables, f, indent=2)
    
    print(f"\nSuccessfully saved {len(variables)} variables to {output_file}")
    
    # Check file size
    file_size_mb = Path(output_file).stat().st_size / (1024*1024)
    print(f"File size: {file_size_mb:.2f} MB")
    
    # Print some statistics
    formulas_count = sum(1 for v in variables.values() if v.get("formula"))
    adds_count = sum(1 for v in variables.values() if v.get("adds"))
    subtracts_count = sum(1 for v in variables.values() if v.get("subtracts"))
    params_count = sum(1 for v in variables.values() if v.get("parameters"))
    desc_count = sum(1 for v in variables.values() if v.get("description"))
    
    print(f"\nStatistics:")
    print(f"- Total variables: {len(variables)}")
    print(f"- Variables with formulas: {formulas_count}")
    print(f"- Variables with adds: {adds_count}")
    print(f"- Variables with subtracts: {subtracts_count}")
    print(f"- Variables with parameters: {params_count}")
    print(f"- Variables with descriptions: {desc_count}")

if __name__ == "__main__":
    main()