# PolicyEngine Variable Dependency Visualizer

An interactive web application that generates dependency flowcharts for PolicyEngine variables in both the US and UK. Simply select a country, type a variable name, and instantly visualize its dependencies as an interactive network graph.

## 🌐 Live Demo

**No setup required! Try it now: https://hua7450.github.io/flow_chart**

Access the fully functional app directly in your browser - no installation needed.

## 🚀 Quick Start (For Local Development)

```bash
# Clone and setup
git clone https://github.com/hua7450/flow_chart.git
cd flow_chart

# Initialize PolicyEngine submodules for US and UK data
git submodule update --init --recursive

# Install dependencies
cd backend && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..

# Run the application
./run_react_app.sh
```

Then open http://localhost:3000 in your browser.

## Features

- 🌍 **Multi-Country Support**: Analyze both US (3,000+ variables) and UK (600+ variables) tax-benefit systems
- 🔍 **Interactive Visualization**: Explore variable dependencies with an interactive network graph
- 📊 **Comprehensive Dependency Types**: Visualize formulas, additions, subtractions, and parameter dependencies
- ⚙️ **Highly Customizable**: Control depth, stop variables, and display options
- 🚀 **Real-time Analysis**: Direct access to PolicyEngine variables with automatic parameter extraction
- 🎨 **Color-Coded Interface**: Different colors for different dependency types and node states
- 📝 **Rich Metadata Display**: View variable labels, descriptions, value types, and parameter values

## Prerequisites

- Python 3.8 or higher
- Node.js 14+ and npm
- Git

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/hua7450/flow_chart.git
cd flow_chart
```

### 2. Initialize PolicyEngine Submodules

```bash
git submodule update --init --recursive
```

### 3. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## Running the Application

### Option 1: Automated Script (Recommended)

```bash
./run_react_app.sh
```

This script will:
- Start the Flask API server on port 5001
- Start the React frontend on port 3000
- Handle proper cleanup when you press Ctrl+C

### Option 2: Manual Start

**Terminal 1 - Backend API:**
```bash
cd backend
python3 api.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

## 🛠 Troubleshooting

### Common Issues and Solutions

#### The site can't be reached when accessing localhost:3000

**Problem**: The React app isn't starting properly when using the script.

**Solutions**:
1. Make sure all dependencies are installed:
   ```bash
   cd frontend && npm install
   ```

2. Check if ports are already in use:
   ```bash
   lsof -i :3000 -i :5001
   ```
   If ports are in use, kill the processes:
   ```bash
   pkill -f "react-scripts"
   pkill -f "python3 api.py"
   ```

3. Try running the services manually in separate terminals (see Option 2 above)

#### API Connection Failed

**Problem**: Frontend can't connect to the backend API.

**Solutions**:
1. Ensure the backend is running and accessible:
   ```bash
   curl http://localhost:5001/api/variables
   ```

2. Check the frontend `.env` file exists and contains:
   ```
   REACT_APP_API_URL=http://localhost:5001
   ```

#### PolicyEngine Data Not Loading

**Problem**: Variables not loading or showing errors.

**Solution**: Ensure the PolicyEngine submodule is properly initialized:
```bash
git submodule update --init --recursive
```

#### Script Permission Denied

**Problem**: `./run_react_app.sh: Permission denied`

**Solution**: Make the script executable:
```bash
chmod +x run_react_app.sh
```

## 📖 Using the Application

### Basic Usage

1. **Select Country**: Choose between United States 🇺🇸 or United Kingdom 🇬🇧 from the dropdown

2. **Enter a Variable Name**: Type any PolicyEngine variable
   - US examples: `household_net_income`, `earned_income_tax_credit`, `snap`
   - UK examples: `universal_credit`, `child_benefit`, `nhs_spending`

3. **Configure Options**:
   - **Maximum Depth**: How many levels deep to traverse dependencies (1-10)
   - **Expand Adds/Subtracts**: Show individual variables in add/subtract operations
   - **Show Labels**: Display variable names on nodes
   - **Show Parameters**: Include parameter dependencies
   - **Stop Variables**: Specify variables where traversal should stop

4. **Generate and Explore**: Click "Generate Flowchart" to create an interactive dependency graph

### Understanding the Graph

#### Node Colors
- **Teal**: Target variable (your starting point)
- **Light Blue**: Regular dependency variables
- **Red Border**: Stop variables (expansion stops here)
- **Purple**: Variables with `defined_for` conditions

#### Edge Types
- **Gray Arrow**: Standard dependency
- **Green Arrow**: Addition operation
- **Red Arrow**: Subtraction operation
- **Purple Arrow**: Applicability condition (`defined_for`)

#### Node Information
Hover over any node to see:
- Variable label and description
- Entity type (Person, TaxUnit, Household, etc.)
- Value type (float, bool, int, Enum)
- Formula variables used
- Parameters and their values
- Add/subtract operations

## Project Structure

```
flow_chart/
├── backend/              # Flask API server
│   ├── api.py           # REST API endpoints
│   ├── requirements.txt # Python dependencies
│   ├── variables/       # Variable extraction logic
│   ├── parameters/      # Parameter handling
│   └── utils/           # Graph building utilities
├── frontend/            # React application
│   ├── src/         
│   │   ├── components/  # UI components
│   │   └── App.js      # Main application
│   ├── package.json     # Node dependencies
│   └── .env            # Environment variables
├── docs/                # Documentation
│   ├── PARAMETER_RULES.md
│   └── VARIABLE_RULES.md
├── policyengine-us/     # PolicyEngine US source (git submodule)
├── policyengine-uk/     # PolicyEngine UK source (git submodule)
└── run_react_app.sh     # Startup script
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

## Updating PolicyEngine Data

To get the latest PolicyEngine variables:

```bash
# Update all submodules
git submodule update --remote

# Or update individually
git submodule update --remote policyengine-us
git submodule update --remote policyengine-uk

# Commit changes
git add .
git commit -m "Update PolicyEngine to latest version"
git push
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