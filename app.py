#!/usr/bin/env python3
"""
PolicyEngine Variable Dependency Flowchart Visualizer
A Streamlit web app that generates interactive dependency flowcharts for PolicyEngine variables.
"""

import streamlit as st
import json
from pathlib import Path
import re
from pyvis.network import Network
import tempfile
from typing import Dict, List, Set, Optional, Tuple

# Import stop variables configuration
from stop_variables_config import DEFAULT_STOP_VARIABLES, OPTIONAL_STOP_VARIABLES

# Page config
st.set_page_config(
    page_title="PolicyEngine Variable Dependency Visualizer",
    page_icon="📊",
    layout="wide"
)

# Cache the variables data
@st.cache_data
def load_variables():
    """Load the pre-fetched variables from JSON file."""
    json_path = Path(__file__).parent / "variables.json"
    
    if not json_path.exists():
        st.error(f"Variables data file not found at {json_path}")
        st.info("Please run `python fetch_variables.py` to download the variables data.")
        return {}
    
    with open(json_path, 'r') as f:
        return json.load(f)

def extract_dependencies_from_variable(variable_data: Dict) -> Dict[str, List[str]]:
    """
    Extract all types of dependencies from a variable's data.
    
    Returns:
        Dictionary with dependency types as keys
    """
    deps = {
        "formula": [],
        "adds": [],
        "subtracts": [],
        "parameters": [],
        "variables": [],
        "defined_for": []
    }
    
    # Get formula dependencies
    if variable_data.get("formula"):
        deps["formula"].append(variable_data["formula"])
    
    # Get adds dependencies
    if variable_data.get("adds"):
        deps["adds"] = variable_data["adds"]
    
    # Get subtracts dependencies
    if variable_data.get("subtracts"):
        deps["subtracts"] = variable_data["subtracts"]
    
    # Get parameter dependencies
    if variable_data.get("parameters"):
        deps["parameters"] = variable_data["parameters"]
    
    # Get variable references in formulas
    if variable_data.get("variables"):
        deps["variables"] = variable_data["variables"]
    
    # Get defined_for conditions
    if variable_data.get("defined_for"):
        deps["defined_for"] = variable_data["defined_for"]
    
    return deps

def build_dependency_graph(
    variables: Dict,
    root_variable: str,
    max_depth: int = 10,
    stop_variables: Set[str] = None,
    expand_adds_subtracts: bool = True,
    show_parameters: bool = True
) -> Dict:
    """
    Build a dependency graph for a given variable.
    
    Args:
        variables: Dictionary of all variables
        root_variable: The variable to start from
        max_depth: Maximum depth to traverse
        stop_variables: Set of variables to stop at
        expand_adds_subtracts: Whether to expand add/subtract operations
    
    Returns:
        Dictionary with nodes and edges for the graph
    """
    if stop_variables is None:
        stop_variables = set()
    
    nodes = {}
    edges = []
    visited = set()
    
    def clean_variable_name(name: str) -> str:
        """Clean up variable names for matching."""
        # Remove quotes and clean up
        name = name.strip().strip('"').strip("'")
        # Replace dots with underscores for parameter names
        name = name.replace(".", "_")
        return name
    
    def traverse(var_name: str, depth: int = 0, parent: Optional[str] = None, edge_type: str = "formula"):
        """Recursively traverse dependencies."""
        if depth > max_depth:
            return
        
        # Clean the variable name
        var_name = clean_variable_name(var_name)
        
        if var_name in visited:
            # Still add the edge even if visited
            if parent:
                edges.append({
                    "from": var_name,
                    "to": parent,
                    "type": edge_type
                })
            return
        
        visited.add(var_name)
        
        # Add node
        node_data = {
            "id": var_name,
            "label": var_name,
            "level": depth,
            "type": "variable"
        }
        
        # Check if this is a stop variable
        if var_name in stop_variables:
            node_data["type"] = "stop"
            nodes[var_name] = node_data
            if parent:
                edges.append({
                    "from": var_name,
                    "to": parent,
                    "type": edge_type
                })
            return
        
        # Get variable data
        var_data = variables.get(var_name, {})
        
        # Enhanced tooltip with comprehensive information
        tooltip_parts = []
        
        # Variable name and label
        tooltip_parts.append(f"<b>{var_name}</b>")
        if var_data.get("label") and var_data["label"] != var_name:
            tooltip_parts.append(f"<i>{var_data['label']}</i>")
        
        # Description
        if var_data.get("description"):
            tooltip_parts.append(f"<br><br>{var_data['description']}")
        
        # Unit
        if var_data.get("unit"):
            tooltip_parts.append(f"<br><b>Unit:</b> {var_data['unit']}")
        
        # File path (for developers)
        if var_data.get("file_path"):
            file_path = var_data["file_path"].replace("policyengine_us/variables/", "")
            tooltip_parts.append(f"<br><b>File:</b> {file_path}")
        
        # Dependency counts
        dep_counts = []
        if var_data.get("adds"):
            dep_counts.append(f"{len(var_data['adds'])} adds")
        if var_data.get("subtracts"):
            dep_counts.append(f"{len(var_data['subtracts'])} subtracts")
        if var_data.get("variables"):
            dep_counts.append(f"{len(var_data['variables'])} variables")
        if var_data.get("parameters"):
            dep_counts.append(f"{len(var_data['parameters'])} parameters")
        if var_data.get("defined_for"):
            dep_counts.append(f"{len(var_data['defined_for'])} conditions")
        
        if dep_counts:
            tooltip_parts.append(f"<br><b>Dependencies:</b> {', '.join(dep_counts)}")
        
        node_data["title"] = "".join(tooltip_parts)
        
        nodes[var_name] = node_data
        
        # Add edge from dependency to parent (reversed direction)
        if parent:
            edges.append({
                "from": var_name,
                "to": parent,
                "type": edge_type
            })
        
        # Process dependencies
        all_deps = extract_dependencies_from_variable(var_data)
        
        # Process defined_for dependencies - expand them to get their dependencies
        for defined_for_var in all_deps["defined_for"]:
            defined_for_var = clean_variable_name(defined_for_var)
            if defined_for_var and defined_for_var != var_name:
                # Get the dependencies of the defined_for variable
                defined_for_data = variables.get(defined_for_var, {})
                if defined_for_data:
                    # Add all its dependencies directly to our variable
                    defined_for_deps = extract_dependencies_from_variable(defined_for_data)
                    
                    # Add defined_for's own defined_for dependencies
                    for subdep in defined_for_deps.get("defined_for", []):
                        subdep = clean_variable_name(subdep)
                        if subdep and subdep != var_name:
                            traverse(subdep, depth + 1, var_name, "defined_for")
                    
                    # Add defined_for's variable dependencies
                    for subdep in defined_for_deps.get("variables", []):
                        subdep = clean_variable_name(subdep)
                        if subdep and subdep != var_name:
                            traverse(subdep, depth + 1, var_name, "formula")
                    
                    # Add defined_for's formula dependency
                    for subdep in defined_for_deps.get("formula", []):
                        subdep = clean_variable_name(subdep)
                        if subdep and subdep != var_name:
                            traverse(subdep, depth + 1, var_name, "formula")
                else:
                    # If we can't expand it, just add it as is
                    traverse(defined_for_var, depth + 1, var_name, "defined_for")
        
        # Process variable references in formulas
        for dep in all_deps["variables"]:
            dep = clean_variable_name(dep)
            if dep and dep != var_name:
                traverse(dep, depth + 1, var_name, "formula")
        
        # Process formula dependencies
        for dep in all_deps["formula"]:
            dep = clean_variable_name(dep)
            if dep and dep != var_name:
                traverse(dep, depth + 1, var_name, "formula")
        
        # Process parameters if enabled
        if show_parameters:
            for dep in all_deps["parameters"]:
                dep = clean_variable_name(dep)
                if dep and dep != var_name:
                    traverse(dep, depth + 1, var_name, "parameter")
        
        # Process adds/subtracts if enabled
        if expand_adds_subtracts:
            for dep in all_deps["adds"]:
                dep = clean_variable_name(dep)
                if dep and dep != var_name:
                    traverse(dep, depth + 1, var_name, "adds")
            
            for dep in all_deps["subtracts"]:
                dep = clean_variable_name(dep)
                if dep and dep != var_name:
                    traverse(dep, depth + 1, var_name, "subtracts")
    
    # Start traversal
    traverse(root_variable)
    
    return {"nodes": nodes, "edges": edges}

def create_flowchart(graph_data: Dict, show_labels: bool = True, show_parameters: bool = True, layout_version: str = "v1") -> str:
    """
    Create an interactive flowchart using pyvis.
    
    Args:
        graph_data: Dictionary with nodes and edges
        show_labels: Whether to show labels on nodes
        show_parameters: Whether to show parameter nodes
    
    Returns:
        HTML string of the network graph
    """
    net = Network(height="800px", width="100%", directed=True)
    
    # Configure physics based on graph size for performance
    num_nodes = len(graph_data["nodes"])
    
    if num_nodes > 100:
        # Simplified physics for large graphs
        net.barnes_hut(
            gravity=-1500,
            central_gravity=0.05,
            spring_length=400,
            spring_strength=0.002,
            damping=0.9,
            overlap=0
        )
    elif num_nodes > 50:
        # Medium optimization with better spacing
        net.barnes_hut(
            gravity=-2000,
            central_gravity=0.1,
            spring_length=450,
            spring_strength=0.003,
            damping=0.7,
            overlap=0
        )
    else:
        if layout_version == "v2":
            # Version 2: Hierarchical tree layout - complete options
            net.set_options('''
            {
                "layout": {
                    "hierarchical": {
                        "enabled": true,
                        "direction": "UD",
                        "sortMethod": "directed",
                        "nodeSpacing": 200,
                        "levelSeparation": 150,
                        "treeSpacing": 200,
                        "blockShifting": true,
                        "edgeMinimization": true,
                        "parentCentralization": true
                    }
                },
                "physics": {
                    "enabled": false
                },
                "nodes": {
                    "shape": "box",
                    "margin": 10,
                    "widthConstraint": {
                        "maximum": 200
                    }
                },
                "edges": {
                    "smooth": {
                        "type": "dynamic"
                    },
                    "arrows": {
                        "to": {
                            "enabled": true,
                            "scaleFactor": 0.5
                        }
                    }
                },
                "interaction": {
                    "dragNodes": true,
                    "hover": true,
                    "navigationButtons": true,
                    "keyboard": true
                }
            }
            ''')
        else:
            # Version 1: Force-directed physics layout
            net.barnes_hut(
                gravity=-2500,
                central_gravity=0.1,
                spring_length=500,
                spring_strength=0.004,
                damping=0.6,
                overlap=0
            )
    
    # Keep track of which nodes were actually added to the visualization
    added_nodes = set()
    
    # Add nodes
    for node_id, node_data in graph_data["nodes"].items():
        # Set node color based on type
        if node_data.get("type") == "stop":
            color = "#ff9999"  # Light red for stop variables
        elif node_data["level"] == 0:
            color = "#90EE90"  # Light green for root
        else:
            color = "#87CEEB"  # Light blue for dependencies
        
        # Prepare node attributes with better styling
        node_attrs = {
            "color": color,
            "font": {"size": 12, "face": "Arial", "color": "#333333"},
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "shape": "box",
            "margin": 8,
            "widthConstraint": {"maximum": 180},
            "heightConstraint": {"minimum": 35}
        }
        
        # Add label if enabled
        label = node_data["label"] if show_labels else ""
        
        # Add title (tooltip) if available
        title = node_data.get("title", node_data["label"])
        
        net.add_node(
            node_id,
            label=label,
            title=title,
            **node_attrs
        )
        added_nodes.add(node_id)
    
    # Add edges
    for edge in graph_data["edges"]:
        from_node = edge["from"]
        to_node = edge["to"]
        
        # Only add edge if both nodes were actually added to the visualization
        if from_node not in added_nodes or to_node not in added_nodes:
            continue
        
        # Set edge color based on type
        if edge["type"] == "adds":
            edge_color = "#00ff00"  # Green for adds
            edge_label = "+"
        elif edge["type"] == "subtracts":
            edge_color = "#ff0000"  # Red for subtracts
            edge_label = "-"
        elif edge["type"] == "defined_for":
            edge_color = "#ff9900"  # Orange for defined_for
            edge_label = "⚡"  # Lightning bolt for conditional
        elif edge["type"] == "parameter":
            edge_color = "#9900ff"  # Purple for parameters
            edge_label = "📊"
        else:
            edge_color = "#666666"  # Gray for formula/variables
            edge_label = ""
        
        net.add_edge(
            from_node,
            to_node,
            color=edge_color,
            label=edge_label,
            arrows="to",
            width=2,
            smooth={"type": "curvedCW", "roundness": 0.1},
            font={"size": 10, "color": "#444444"}
        )
    
    # Set options with performance optimization (skip for hierarchical layout)
    if layout_version != "v2":
        stabilization_iterations = 50 if num_nodes > 100 else 100 if num_nodes > 50 else 200
        hide_on_drag = num_nodes > 80  # Hide edges/nodes during drag for large graphs
        
        net.set_options(f"""
    var options = {{
        "nodes": {{
            "shape": "box",
            "margin": 10,
            "widthConstraint": {{
                "maximum": 200
            }}
        }},
        "edges": {{
            "smooth": {{
                "type": "dynamic"
            }},
            "arrows": {{
                "to": {{
                    "enabled": true,
                    "scaleFactor": 0.5
                }}
            }}
        }},
        "physics": {{
            "enabled": true,
            "stabilization": {{
                "enabled": true,
                "iterations": {stabilization_iterations}
            }}
        }},
        "interaction": {{
            "dragNodes": true,
            "hideEdgesOnDrag": {str(hide_on_drag).lower()},
            "hideNodesOnDrag": {str(hide_on_drag).lower()},
            "hover": true,
            "navigationButtons": true,
            "keyboard": true
        }}
    }}
    """)
    
    # Generate HTML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        net.save_graph(f.name)
        with open(f.name, 'r') as html_file:
            html_content = html_file.read()
    
    return html_content

def main():
    """Main Streamlit app."""
    st.title("📊 PolicyEngine Variable Dependency Visualizer")
    st.markdown("""
    This tool generates interactive dependency flowcharts for PolicyEngine variables.
    Enter a variable name below to visualize its dependencies.
    """)
    
    # Load variables
    variables = load_variables()
    
    if not variables:
        st.stop()
    
    # Create two columns for layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("Configuration")
        
        # Variable input with search
        input_method = st.radio(
            "Choose input method:",
            ["🔍 Search from list", "⌨️ Type manually"],
            horizontal=True
        )
        
        if input_method == "🔍 Search from list":
            # Initialize session state for selected variable if not exists
            if 'selected_variable' not in st.session_state:
                st.session_state.selected_variable = ""
            
            # Create searchable selectbox with all variables
            all_variable_names = sorted(variables.keys())
            
            # Add some popular variables at the top
            popular_vars = [
                "household_net_income", "federal_income_tax", "eitc", "snap", 
                "dc_agi", "ca_income_tax", "medicaid", "ssi", "social_security"
            ]
            popular_available = [v for v in popular_vars if v in variables]
            
            # Combine popular + all others
            if popular_available:
                st.write("**Popular variables:**")
                popular_cols = st.columns(min(3, len(popular_available)))
                for i, var in enumerate(popular_available):
                    with popular_cols[i % len(popular_cols)]:
                        if st.button(var, key=f"pop_{var}"):
                            st.session_state.selected_variable = var
                
                # Use selectbox with the session state value
                variable_name = st.selectbox(
                    "Or search all variables:",
                    [""] + all_variable_names,
                    index=all_variable_names.index(st.session_state.selected_variable) + 1 if st.session_state.selected_variable in all_variable_names else 0,
                    help=f"Search among {len(all_variable_names)} PolicyEngine variables",
                    key="variable_selectbox"
                )
                
                # Update session state if selectbox changes
                if variable_name and variable_name != st.session_state.selected_variable:
                    st.session_state.selected_variable = variable_name
                elif not variable_name:
                    variable_name = st.session_state.selected_variable
            else:
                variable_name = st.selectbox(
                    "Select Variable:",
                    [""] + all_variable_names,
                    help=f"Search among {len(all_variable_names)} PolicyEngine variables"
                )
        else:
            variable_name = st.text_input(
                "Variable Name",
                placeholder="e.g., household_net_income",
                help="Enter the name of the PolicyEngine variable to visualize"
            )
        
        # Advanced options
        with st.expander("Advanced Options"):
            max_depth = st.slider(
                "Maximum Depth",
                min_value=1,
                max_value=20,
                value=10,
                help="Maximum depth to traverse in the dependency tree"
            )
            
            expand_adds_subtracts = st.checkbox(
                "Expand Adds/Subtracts",
                value=True,
                help="Show variables used in add/subtract operations"
            )
            
            show_labels = st.checkbox(
                "Show Labels",
                value=True,
                help="Display variable names on nodes"
            )
            
            show_parameters = st.checkbox(
                "Show Parameters",
                value=True,
                help="Display parameter dependencies"
            )
            
            # Layout version toggle
            layout_version = st.radio(
                "Layout Style",
                ["v1", "v2"],
                format_func=lambda x: "Version 1 (Force-directed)" if x == "v1" else "Version 2 (Hierarchical Tree)",
                help="Version 1: Physics-based layout with flexible positioning\nVersion 2: Tree structure with inputs at bottom, target at top"
            )
            
            # User-defined stop variables (optional)
            stop_variables_input = st.text_area(
                "Stop Variables (optional)",
                placeholder="employment_income\nself_employment_income\npension_income",
                help="Add variables to stop at if the graph is too complex. These won't expand their dependencies.",
                height=100
            )
            
            # Parse user input
            custom_stops = [v.strip() for v in stop_variables_input.split('\n') if v.strip()]
            
            # Combine with hidden default stops (DEFAULT_STOP_VARIABLES work silently in background)
            stop_variables = set(DEFAULT_STOP_VARIABLES + custom_stops)
        
        # Generate button
        generate_button = st.button("Generate Flowchart", type="primary", use_container_width=True)
        
        # Add performance warning if settings might create large graphs
        if max_depth > 15 or (expand_adds_subtracts and max_depth > 10):
            st.warning("⚠️ **Large Graph Warning:** These settings may create very large graphs. Consider:\n"
                      "- Reducing max depth to 10 or less\n" 
                      "- Adding stop variables\n"
                      "- Disabling 'Expand Adds/Subtracts' for initial exploration")
    
    with col2:
        st.header("Dependency Flowchart")
        
        if generate_button and variable_name:
            # Clean the input variable name
            variable_name = variable_name.strip()
            
            # Check if variable exists
            if variable_name not in variables:
                st.error(f"Variable '{variable_name}' not found in the database.")
                st.info("Available variables (showing first 20):")
                available = list(variables.keys())[:20]
                st.code('\n'.join(available))
            else:
                with st.spinner("Building dependency graph..."):
                    # Build the graph
                    graph_data = build_dependency_graph(
                        variables,
                        variable_name,
                        max_depth=max_depth,
                        stop_variables=stop_variables,
                        expand_adds_subtracts=expand_adds_subtracts,
                        show_parameters=show_parameters
                    )
                    
                    # Check graph size and warn if very large
                    num_nodes = len(graph_data['nodes'])
                    num_edges = len(graph_data['edges'])
                    
                    if num_nodes > 100:
                        st.warning(f"🐌 **Large Graph:** {num_nodes} nodes and {num_edges} edges. "
                                 f"Rendering may be slow. Consider adding more stop variables or reducing depth.")
                    elif num_nodes > 50:
                        st.info(f"📊 **Medium Graph:** {num_nodes} nodes and {num_edges} edges. This may take a moment to render.")
                    else:
                        st.success(f"✅ **Manageable Graph:** {num_nodes} nodes and {num_edges} edges")
                    
                    # Create and display the flowchart
                    html_content = create_flowchart(
                        graph_data,
                        show_labels=show_labels,
                        show_parameters=show_parameters,
                        layout_version=layout_version
                    )
                    
                    # Display the interactive graph
                    st.components.v1.html(html_content, height=800, scrolling=True)
                    
                    # Show legend
                    with st.expander("Legend"):
                        st.markdown("""
                        **Nodes:**
                        - 🟢 **Green Node**: Root variable (starting point)
                        - 🔵 **Blue Nodes**: Dependencies (contribute to parent)
                        - 🔴 **Red Nodes**: Stop variables
                        
                        **Edges (Arrows point toward calculated variable):**
                        - ➕ **Green (+)**: Added to parent variable
                        - ➖ **Red (-)**: Subtracted from parent variable
                        - ⚡ **Orange**: Conditional dependency (defined_for)
                        - 📊 **Purple**: Parameter dependency
                        - ➡️ **Gray**: Formula/variable reference
                        """)
        elif generate_button:
            st.warning("Please enter a variable name.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <small>
        Data source: <a href='https://github.com/policyengine/policyengine-us'>PolicyEngine US</a> | 
        Built with Streamlit and PyVis
        </small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()