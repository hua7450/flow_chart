# PolicyEngine Variable Dependency Visualizer

An interactive web application that generates dependency flowcharts for PolicyEngine variables. Simply type a variable name and instantly visualize its dependencies as an interactive network graph.

## Features

- 🔍 **Interactive Visualization**: Explore variable dependencies with an interactive network graph
- 📊 **Comprehensive Dependency Types**: Visualize formulas, additions, subtractions, and parameter dependencies
- ⚙️ **Highly Customizable**: Control depth, stop variables, and display options
- 🚀 **Real-time Analysis**: Direct access to PolicyEngine variables with automatic parameter extraction
- 🎨 **Color-Coded Interface**: Different colors for different dependency types and node states
- 📝 **Rich Metadata Display**: View variable labels, descriptions, value types, and parameter values

## Architecture

```
flow_chart/
├── backend/           # Flask API server
│   ├── api.py        # REST API endpoints
│   ├── variables/    # Variable extraction logic
│   ├── parameters/   # Parameter handling
│   └── utils/        # Graph building utilities
├── frontend/         # React application
│   ├── src/         
│   │   ├── components/  # UI components
│   │   └── App.js      # Main application
│   └── package.json
├── docs/             # Documentation
│   ├── PARAMETER_RULES.md
│   └── VARIABLE_RULES.md
└── policyengine-us/  # PolicyEngine source (git submodule)
```

## Installation

### Prerequisites
- Python 3.8+
- Node.js 14+ and npm
- Git

### Setup Steps

1. **Clone the repository:**
```bash
git clone https://github.com/hua7450/flow_chart.git
cd flow_chart
```

2. **Initialize the PolicyEngine submodule:**
```bash
git submodule update --init --recursive
```

3. **Install backend dependencies:**
```bash
cd backend
pip install -r requirements.txt
cd ..
```

4. **Install frontend dependencies:**
```bash
cd frontend
npm install
cd ..
```

## Running the Application

### Quick Start (Both Servers)
```bash
./run_react_app.sh
```
This will start both the Flask API (port 5001) and React frontend (port 3000).

### Manual Start

**Backend API:**
```bash
cd backend
python3 api.py
```
The API will be available at `http://localhost:5001`

**Frontend:**
```bash
cd frontend
npm start
```
The app will open at `http://localhost:3000`

## Using the Application

1. **Enter a Variable Name**: Type any PolicyEngine variable (e.g., `household_net_income`, `spm_unit_fpg`)

2. **Configure Options**:
   - **Maximum Depth**: How many levels deep to traverse dependencies (1-10)
   - **Expand Adds/Subtracts**: Show individual variables in add/subtract operations
   - **Show Labels**: Display variable names on nodes
   - **Show Parameters**: Include parameter dependencies
   - **Stop Variables**: Specify variables where traversal should stop

3. **Generate and Explore**: Click "Generate Flowchart" to create an interactive dependency graph

## Graph Visualization

### Node Colors
- **Teal**: Target variable (your starting point)
- **Light Blue**: Regular dependency variables
- **Red Border**: Stop variables (expansion stops here)
- **Purple**: Variables with `defined_for` conditions

### Edge Types
- **Gray Arrow**: Standard dependency
- **Green Arrow**: Addition operation
- **Red Arrow**: Subtraction operation
- **Purple Arrow**: Applicability condition (`defined_for`)

### Node Information
Hover over any node to see:
- Variable label and description
- Entity type (Person, TaxUnit, Household, etc.)
- Value type (float, bool, int, Enum)
- Formula variables used
- Parameters and their values
- Add/subtract operations

## Advanced Features

### Parameter Extraction
The system automatically extracts and displays:
- Direct parameter assignments
- Nested parameter access
- Bracket parameters with thresholds
- Subscripted parameters (e.g., state-specific values)
- Parameter lists that expand to variables

### Stop Variables
Built-in stop variables prevent infinite recursion:
- Basic demographics: `age`, `is_child`, `is_adult`
- Geographic: `state_code`, `county`
- Income sources: `employment_income`, `self_employment_income`
- Identifiers: `is_tax_unit_head`, `is_household_head`

## Updating PolicyEngine Data

To get the latest PolicyEngine variables:

```bash
# Update the submodule
git submodule update --remote policyengine-us
git add policyengine-us
git commit -m "Update PolicyEngine to latest version"
git push
```

## API Documentation

### REST Endpoints

**Get all variables:**
```
GET /api/variables
```

**Get variable details:**
```
GET /api/variable/<variable_name>
```

**Generate dependency graph:**
```
GET /api/graph/<variable_name>?depth=3&expand_adds=true&show_labels=true
```

## Development

### Backend Development
The backend uses Flask and provides REST APIs for variable extraction and graph generation. Key modules:
- `variable_extractor.py`: AST parsing for Python code analysis
- `graph_builder.py`: Constructs network graphs from dependencies
- `parameter_handler.py`: Loads and processes YAML parameter files

### Frontend Development
The React frontend uses vis-network for graph visualization. To modify:
```bash
cd frontend
npm start  # Development server with hot reload
npm run build  # Production build
```

## Documentation

- [Parameter Extraction Rules](docs/PARAMETER_RULES.md) - How parameters are extracted and displayed
- [Variable Extraction Rules](docs/VARIABLE_RULES.md) - How variables and dependencies are identified

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project uses data from PolicyEngine US, which is licensed under the AGPL-3.0 License.

## Support

For issues or questions, please open an issue on [GitHub](https://github.com/hua7450/flow_chart/issues).