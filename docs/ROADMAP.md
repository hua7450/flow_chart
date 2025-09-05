# 🗺️ PolicyEngine Variable Visualizer - Roadmap

## ✅ Completed Features
- [x] Download and parse all PolicyEngine variables
- [x] Extract all dependency types (adds, subtracts, parameters, variables, defined_for)
- [x] Interactive flowchart visualization with vis.js
- [x] Reverse arrow direction (dependencies flow into calculated variables)
- [x] Color-coded edges for different dependency types
- [x] Configurable options (depth, stop variables, expand adds/subtracts)
- [x] Pre-fetched JSON for instant loading

## 🚀 Planned Improvements

### 1. Search/Autocomplete for Variable Names (Priority: High)
**Goal:** Make it easier to find and select variables
- [ ] Add searchable dropdown/selectbox with all variable names
- [ ] Show variable description in dropdown
- [ ] Support fuzzy search
- [ ] Add "Recently viewed" section
- [ ] Group variables by category (tax, benefits, income, etc.)

### 2. Export Flowchart as Image (Priority: High)
**Goal:** Allow users to save and share flowcharts
- [ ] Add "Download as PNG" button
- [ ] Add "Download as SVG" button (vector format)
- [ ] Option to include/exclude legend in export
- [ ] Custom resolution settings
- [ ] Copy to clipboard functionality

### 3. Enhanced Tooltips (Priority: Medium)
**Goal:** Show more context without cluttering the graph
- [ ] Show full variable description on hover
- [ ] Display variable metadata (unit, label, file path)
- [ ] Show example values or ranges
- [ ] Quick link to PolicyEngine documentation
- [ ] Show number of dependencies

### 4. Save/Share Configurations (Priority: Medium)
**Goal:** Let users save and share specific views
- [ ] Generate shareable URL with encoded settings
- [ ] Save multiple "views" locally
- [ ] Bookmark favorite variables
- [ ] Share button with shortened URL
- [ ] Embed code generator for websites

### 5. Optimize Large Graphs (Priority: High)
**Goal:** Better performance with complex dependencies
- [ ] Progressive loading for deep graphs
- [ ] Cluster similar nodes
- [ ] Collapsible node groups
- [ ] Mini-map for navigation
- [ ] Performance mode (simplified rendering)
- [ ] Warning before rendering very large graphs

### 6. Additional Features (Priority: Low-Medium)

#### Search & Discovery
- [ ] Full-text search across all variables
- [ ] "Find path between two variables"
- [ ] List all variables that depend on selected variable (reverse dependencies)
- [ ] Variable statistics dashboard

#### Visualization Enhancements
- [ ] Multiple layout algorithms (hierarchical, circular, force-directed)
- [ ] 3D visualization option
- [ ] Animate dependency flow
- [ ] Side-by-side comparison of two variables
- [ ] Dark mode

#### Data & Analysis
- [ ] Show parameter values from specific year
- [ ] Highlight recently changed variables
- [ ] Export dependency data as CSV/JSON
- [ ] API endpoint for programmatic access
- [ ] Integration with PolicyEngine calculator

#### User Experience
- [ ] Keyboard shortcuts
- [ ] Undo/redo navigation
- [ ] Help tour for first-time users
- [ ] Mobile-responsive design
- [ ] Accessibility improvements (screen reader support)

## 📊 Technical Improvements

### Performance
- [ ] Lazy load variables.json
- [ ] Cache rendered graphs
- [ ] Web worker for graph processing
- [ ] Virtualization for large node lists

### Code Quality
- [ ] Add unit tests
- [ ] Type hints throughout
- [ ] Automated testing with GitHub Actions
- [ ] Code documentation
- [ ] Contribution guidelines

### Deployment
- [ ] Docker container
- [ ] One-click deploy buttons (Heroku, Railway, etc.)
- [ ] CDN for static assets
- [ ] Performance monitoring

## 🎯 Version Milestones

### v1.1 - Better Discovery (Next Release)
- Search/autocomplete
- Export as image
- Enhanced tooltips

### v1.2 - Sharing & Collaboration
- Shareable URLs
- Save configurations
- Embed widgets

### v1.3 - Performance & Scale
- Large graph optimizations
- Alternative layouts
- Progressive loading

### v2.0 - Advanced Features
- Reverse dependency search
- Parameter value integration
- API access
- PolicyEngine calculator integration

## 💡 Ideas for Future Exploration
- Machine learning to suggest related variables
- Automated documentation generation
- Variable impact analysis
- Change detection between PolicyEngine versions
- Natural language search ("show me all tax credits")

---

**Contributing:** Feel free to open an issue or PR for any of these features!
**Feedback:** Please share your ideas and use cases!