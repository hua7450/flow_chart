#!/usr/bin/env python3
"""
Enhanced variable extraction module with improved parameter extraction.
Handles multi-line parameter assignments and bracket parameters.
"""

import ast
from typing import Dict, List, Optional, Set
from pathlib import Path


class ParameterExtractorVisitor(ast.NodeVisitor):
    """AST visitor to extract parameter assignments and usage."""
    
    def __init__(self):
        self.parameters = {}  # param_name -> param_path
        self.direct_parameters = {}  # Direct assignments like limit = parameters(period).xxx
        self.bracket_parameters = {}  # Parameters with .calc() method
        self.parameter_vars = {}  # Variable assignments like p = parameters(period).xxx
        
    def visit_Assign(self, node):
        """Visit assignment nodes to extract parameter assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                
                # Check for parameters(period) assignment
                if self._is_parameters_call(node.value):
                    # Extract the parameter path
                    param_path = self._extract_parameter_path_from_call(node.value)
                    if param_path:
                        # Store as a parameter variable (like p = parameters(period).gov.states.ma...)
                        self.parameter_vars[var_name] = param_path
                        self.parameters[var_name] = param_path
                
                # Check for direct parameter access (limit = parameters(period).xxx.REDUCED)
                elif isinstance(node.value, ast.Attribute):
                    param_path = self._extract_direct_parameter_path(node.value)
                    if param_path:
                        # Check if this looks like a complete parameter (ends with uppercase)
                        path_parts = param_path.split('.')
                        if path_parts and path_parts[-1].isupper():
                            self.direct_parameters[var_name] = param_path
                
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Visit call nodes to find .calc() usage."""
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'calc':
            # This is a .calc() call - check what it's being called on
            if isinstance(node.func.value, ast.Name):
                # It's being called on a variable (like p.calc())
                var_name = node.func.value.id
                if var_name in self.parameter_vars:
                    # Mark this as a bracket parameter
                    self.bracket_parameters[var_name] = self.parameter_vars[var_name]
        
        self.generic_visit(node)
    
    def _is_parameters_call(self, node):
        """Check if a node is a parameters(period) call or attribute chain from it."""
        if isinstance(node, ast.Call):
            # Direct parameters(period) call
            if isinstance(node.func, ast.Name) and node.func.id == 'parameters':
                return True
        elif isinstance(node, ast.Attribute):
            # Attribute chain from parameters(period)
            return self._has_parameters_base(node)
        return False
    
    def _has_parameters_base(self, node):
        """Check if an attribute chain has parameters(period) at its base."""
        current = node
        while isinstance(current, ast.Attribute):
            current = current.value
        
        if isinstance(current, ast.Call):
            if isinstance(current.func, ast.Name) and current.func.id == 'parameters':
                return True
        return False
    
    def _extract_parameter_path_from_call(self, node):
        """Extract parameter path from a parameters(period).xxx chain."""
        if isinstance(node, ast.Call):
            # Just parameters(period) with no attributes
            return ""
        elif isinstance(node, ast.Attribute):
            # Extract the full path
            path_parts = []
            current = node
            
            while isinstance(current, ast.Attribute):
                path_parts.append(current.attr)
                current = current.value
            
            # Should end with parameters(period) call
            if isinstance(current, ast.Call):
                path_parts.reverse()
                return '.'.join(path_parts)
        
        return None
    
    def _extract_direct_parameter_path(self, node):
        """Extract parameter path from direct access like parameters(period).xxx.REDUCED."""
        path_parts = []
        current = node
        
        while isinstance(current, ast.Attribute):
            path_parts.append(current.attr)
            current = current.value
        
        # Check if this starts with parameters(period)
        if isinstance(current, ast.Call):
            if isinstance(current.func, ast.Name) and current.func.id == 'parameters':
                path_parts.reverse()
                return '.'.join(path_parts)
        
        return None


class EnhancedVariableExtractor:
    """Enhanced extractor with better parameter handling."""
    
    def __init__(self, base_path: str = "../policyengine-us/policyengine_us/variables"):
        self.base_path = Path(base_path)
        # Import the parameter handler
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        from backend.parameters.parameter_handler import ParameterHandler
        self.param_handler = ParameterHandler()
    
    def extract_enhanced_metadata(self, file_path: Path, variable_name: str) -> Dict:
        """Extract enhanced metadata including bracket parameters."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Find the variable class
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == variable_name:
                    # Find the formula method
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == 'formula':
                            # Use the visitor to extract parameters
                            visitor = ParameterExtractorVisitor()
                            visitor.visit(item)
                            
                            # Process the extracted parameters
                            metadata = {
                                'parameters': visitor.parameters,
                                'direct_parameters': visitor.direct_parameters,
                                'bracket_parameters': visitor.bracket_parameters,
                                'parameter_details': {}
                            }
                            
                            # Load parameter details
                            for param_name, param_path in visitor.bracket_parameters.items():
                                param_data = self.param_handler.load_parameter(param_path)
                                if param_data and 'brackets' in param_data:
                                    bracket_info = self._format_bracket_parameter(param_data)
                                    metadata['parameter_details'][param_name] = {
                                        'path': param_path,
                                        'type': 'bracket',
                                        'brackets': bracket_info,
                                        'description': param_data.get('description', '')
                                    }
                            
                            # Load direct parameter details
                            for param_name, param_path in visitor.direct_parameters.items():
                                param_data = self.param_handler.load_parameter(param_path)
                                if param_data:
                                    metadata['parameter_details'][param_name] = {
                                        'path': param_path,
                                        'type': 'direct',
                                        'value': self.param_handler.format_value(param_data, param_name, 'Summary')
                                    }
                            
                            return metadata
            
        except Exception as e:
            print(f"Error extracting enhanced metadata from {file_path}: {e}")
        
        return {}
    
    def _format_bracket_parameter(self, param_data):
        """Format bracket parameter data for display."""
        brackets = param_data.get('brackets', [])
        formatted_brackets = []
        
        for bracket in brackets:
            threshold = bracket.get('threshold', {})
            amount = bracket.get('amount', {})
            
            # Get the latest values
            latest_threshold = None
            latest_amount = None
            
            if isinstance(threshold, dict):
                latest_date = max(threshold.keys()) if threshold else None
                latest_threshold = threshold.get(latest_date) if latest_date else None
            
            if isinstance(amount, dict):
                latest_date = max(amount.keys()) if amount else None
                latest_amount = amount.get(latest_date) if latest_date else None
            
            formatted_brackets.append({
                'threshold': latest_threshold,
                'amount': latest_amount
            })
        
        return formatted_brackets