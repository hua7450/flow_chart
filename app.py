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
                    "from": parent,
                    "to": var_name,
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
                    "from": parent,
                    "to": var_name,
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
        
        # Process defined_for dependencies (always show these)
        for dep in all_deps["defined_for"]:
            dep = clean_variable_name(dep)
            if dep and dep != var_name:
                traverse(dep, depth + 1, var_name, "defined_for")
        
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

def create_flowchart(graph_data: Dict, show_labels: bool = True, show_parameters: bool = True) -> str:
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
            gravity=-3000,
            central_gravity=0.1,
            spring_length=150,
            spring_strength=0.005,
            damping=0.6,
            overlap=0
        )
    elif num_nodes > 50:
        # Medium optimization
        net.barnes_hut(
            gravity=-5000,
            central_gravity=0.2,
            spring_length=180,
            spring_strength=0.008,
            damping=0.5,
            overlap=0
        )
    else:
        # Full physics for small graphs
        net.barnes_hut(
            gravity=-8000,
            central_gravity=0.3,
            spring_length=200,
            spring_strength=0.01,
            damping=0.4,
            overlap=0
        )
    
    # Add nodes
    for node_id, node_data in graph_data["nodes"].items():
        if not show_parameters and "_" in node_id and node_data.get("type") == "variable":
            # Skip parameter nodes if not showing them
            continue
        
        # Set node color based on type
        if node_data.get("type") == "stop":
            color = "#ff9999"  # Light red for stop variables
        elif node_data["level"] == 0:
            color = "#90EE90"  # Light green for root
        else:
            color = "#87CEEB"  # Light blue for dependencies
        
        # Prepare node attributes
        node_attrs = {
            "color": color,
            "font": {"size": 14},
            "borderWidth": 2,
            "borderWidthSelected": 4
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
    
    # Add edges
    for edge in graph_data["edges"]:
        from_node = edge["from"]
        to_node = edge["to"]
        
        # Skip edges from parameter nodes if not showing them
        if not show_parameters and "_" in from_node:
            node_data = graph_data["nodes"].get(from_node, {})
            if node_data.get("type") == "variable":
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
            smooth={"type": "dynamic"}
        )
    
    # Set options with performance optimization
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
                selected_popular = None
                for i, var in enumerate(popular_available):
                    with popular_cols[i % len(popular_cols)]:
                        if st.button(var, key=f"pop_{var}"):
                            selected_popular = var
                
                if selected_popular:
                    variable_name = selected_popular
                else:
                    variable_name = st.selectbox(
                        "Or search all variables:",
                        [""] + all_variable_names,
                        help=f"Search among {len(all_variable_names)} PolicyEngine variables"
                    )
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
            
            # Stop variables
            stop_variables_input = st.text_area(
                "Stop Variables (one per line)",
                placeholder="employment_income\nself_employment_income",
                help="Variables to stop at (won't expand their dependencies)"
            )
            
            stop_variables = set()
            if stop_variables_input:
                stop_variables = {v.strip() for v in stop_variables_input.split('\n') if v.strip()}
        
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
                        show_parameters=show_parameters
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