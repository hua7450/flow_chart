# PolicyEngine Variable Dependency Visualizer

An interactive web application that generates dependency flowcharts for PolicyEngine variables. Simply type a variable name and instantly visualize its dependencies.

## Features

- 🔍 **Interactive Visualization**: Explore variable dependencies with an interactive network graph
- 📊 **Dependency Types**: Visualize formulas, additions, subtractions, and parameter dependencies
- ⚙️ **Customizable**: Control depth, stop variables, and display options
- 🚀 **Fast & Offline**: Pre-fetched data means instant loading with no API calls
- 🎨 **Color-Coded**: Different colors for different dependency types

## Installation

1. Clone the repository:
```bash
git clone https://github.com/hua7450/flow_chart.git
cd flow_chart
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running Locally

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

### Using the App

1. Enter a PolicyEngine variable name (e.g., `household_net_income`)
2. Configure options (optional):
   - **Maximum Depth**: How deep to traverse dependencies
   - **Expand Adds/Subtracts**: Show variables used in add/subtract operations
   - **Show Labels**: Display variable names on nodes
   - **Show Parameters**: Display parameter dependencies
   - **Stop Variables**: Variables to stop at (won't expand their dependencies)
3. Click "Generate Flowchart"

### Updating Variable Data

The app uses pre-fetched variable data from PolicyEngine. To update the data:

```bash
python fetch_variables.py
```

This will download the latest variables from the PolicyEngine US repository and save them to `variables.json`.

## Graph Legend

- **Green Node**: Root variable (starting point)
- **Blue Nodes**: Dependencies
- **Red Nodes**: Stop variables
- **Green Edges**: Addition operations
- **Red Edges**: Subtraction operations
- **Gray Edges**: Formula/parameter dependencies

## Deployment

This app can be deployed on [Streamlit Cloud](https://streamlit.io/cloud):

1. Push to GitHub
2. Connect your GitHub repository to Streamlit Cloud
3. Deploy with one click

## Technical Details

- **Data Source**: [PolicyEngine US](https://github.com/policyengine/policyengine-us)
- **Frontend**: Streamlit
- **Visualization**: PyVis (vis-network)
- **Data Storage**: Local JSON file (~1MB)

## License

This project uses data from PolicyEngine US, which is licensed under the AGPL-3.0 License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.