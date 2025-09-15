import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { Network } from 'vis-network/standalone';
import axios from 'axios';
import PolicyEngineTheme from './theme';

// Types
interface Variable {
  name: string;
  label: string;
  hasParameters: boolean;
}

interface GraphNode {
  id: string;
  label: string;
  title: string;
  level: number;
  color: string;
  shape: string;
  font: { size: number };
}

interface GraphEdge {
  from: string;
  to: string;
  color: string;
  arrows: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5001/api';

// Icon components
const SearchIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8"></circle>
    <path d="m21 21-4.35-4.35"></path>
  </svg>
);

const ChevronIcon = ({ open }: { open: boolean }) => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    style={{ transform: open ? 'rotate(180deg)' : 'rotate(0)', transition: 'transform 0.2s' }}>
    <polyline points="6 9 12 15 18 9"></polyline>
  </svg>
);

const ClearIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);

const LoadingSpinner = () => (
  <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
);

function App() {
  const [variables, setVariables] = useState<Variable[]>([]);
  const [selectedVariable, setSelectedVariable] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [showSearchResults, setShowSearchResults] = useState<boolean>(false);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [detailsOpen, setDetailsOpen] = useState<boolean>(false);
  const [selectedCountry, setSelectedCountry] = useState<string>('US');
  const [variableCount, setVariableCount] = useState<number>(0);
  
  // Controls
  const [maxDepth, setMaxDepth] = useState<number>(10);
  const [expandAddsSubtracts, setExpandAddsSubtracts] = useState<boolean>(true);
  const [showLabels, setShowLabels] = useState<boolean>(true);
  const [showParameters, setShowParameters] = useState<boolean>(true);
  const [paramDetailLevel, setParamDetailLevel] = useState<string>('Summary');
  const [stopVariables, setStopVariables] = useState<string>('');
  const [noParamsList, setNoParamsList] = useState<string>('');
  const [legendExpanded, setLegendExpanded] = useState<boolean>(true);
  
  const networkContainer = useRef<HTMLDivElement>(null);
  const networkInstance = useRef<Network | null>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Load variables on mount and when country changes
  useEffect(() => {
    loadVariables();
  }, [selectedCountry]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setShowSearchResults(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const loadVariables = async () => {
    try {
      const response = await axios.get(`${API_BASE}/variables`, {
        params: { country: selectedCountry }
      });
      if (response.data.success) {
        setVariables(response.data.variables);
        setVariableCount(response.data.total);
      }
    } catch (err) {
      setError('Failed to load variables');
      console.error(err);
    }
  };

  const searchVariables = async (query: string) => {
    if (query.length < 2) {
      setShowSearchResults(false);
      return;
    }
    
    try {
      const response = await axios.get(`${API_BASE}/search`, {
        params: { q: query, country: selectedCountry }
      });
      if (response.data.success) {
        setVariables(response.data.results);
        setShowSearchResults(true);
      }
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  const selectVariable = (variableName: string) => {
    setSelectedVariable(variableName);
    setSearchTerm('');
    setShowSearchResults(false);
    setError('');
    loadVariables();
  };

  const generateFlowchart = async () => {
    if (!selectedVariable) {
      setError('Please select a variable');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE}/graph`, {
        variable: selectedVariable,
        country: selectedCountry,
        maxDepth,
        expandAddsSubtracts,
        showParameters,
        paramDetailLevel,
        showLabels,
        stopVariables: stopVariables.split('\n').filter(v => v.trim()),
        noParamsList: noParamsList.split('\n').filter(v => v.trim())
      });

      if (response.data.success) {
        setGraphData(response.data.graph);
        renderGraph(response.data.graph);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to generate graph');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const renderGraph = (data: GraphData) => {
    if (!networkContainer.current) return;

    // Destroy existing network if it exists
    if (networkInstance.current) {
      networkInstance.current.destroy();
    }

    const options = {
      layout: {
        hierarchical: {
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed',
          nodeSpacing: 300,
          levelSeparation: 150,
          treeSpacing: 200,
          blockShifting: false,
          edgeMinimization: true,
          parentCentralization: true
        }
      },
      autoResize: true,
      physics: {
        enabled: false
      },
      nodes: {
        borderWidth: 2,
        borderWidthSelected: 4,
        margin: { top: 10, right: 15, bottom: 10, left: 15 },
        widthConstraint: { maximum: 250 },
        heightConstraint: { minimum: 40 },
        font: {
          size: 14,
          face: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
          bold: {
            face: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
          }
        },
        shape: 'box',
        shadow: {
          enabled: true,
          color: 'rgba(0,0,0,0.15)',
          size: 12,
          x: 2,
          y: 3
        },
        chosen: {
          node: function(values: any, id: any, selected: any, hovering: any) {
            if (hovering) {
              values.borderWidth = 3;
              values.shadow = true;
              values.shadowSize = 16;
            }
          },
          label: false
        }
      },
      edges: {
        smooth: {
          enabled: true,
          type: 'cubicBezier',
          roundness: 0.5
        },
        width: 2,
        arrows: {
          to: {
            enabled: true,
            scaleFactor: 1.2
          }
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        zoomView: true,
        dragView: true,
        navigationButtons: false,  // Disabled navigation buttons
        keyboard: {
          enabled: false  // Disabled to prevent conflicts with search
        }
      }
    };

    // Create new network
    networkInstance.current = new Network(
      networkContainer.current,
      { nodes: data.nodes, edges: data.edges },
      options
    );

    // After initial render, fix overlapping by ensuring proper spacing
    setTimeout(() => {
      if (!networkInstance.current) return;
      
      const positions = networkInstance.current.getPositions();
      if (!positions) return;
      
      // Group nodes by their Y position (level)
      const levels: Map<number, string[]> = new Map();
      
      for (const nodeId in positions) {
        const y = Math.round(positions[nodeId].y / 10) * 10; // Round to nearest 10 for grouping
        if (!levels.has(y)) {
          levels.set(y, []);
        }
        levels.get(y)!.push(nodeId);
      }
      
      // For each level, ensure proper spacing
      const minSpacing = 180; // Minimum horizontal spacing
      
      levels.forEach((nodesAtLevel) => {
        if (nodesAtLevel.length <= 1) return;
        
        // Sort nodes by current X position
        nodesAtLevel.sort((a, b) => positions[a].x - positions[b].x);
        
        // Calculate total width needed
        const totalWidth = (nodesAtLevel.length - 1) * minSpacing;
        const startX = -totalWidth / 2;
        
        // Position nodes with equal spacing
        nodesAtLevel.forEach((nodeId, index) => {
          const newX = startX + (index * minSpacing);
          networkInstance.current?.moveNode(nodeId, newX, positions[nodeId].y);
        });
      });
      
      // Fit the view to show all nodes (without animation to avoid zoom issues)
      networkInstance.current.fit();
    }, 100);

    // Add hover effects
    networkInstance.current.on("hoverNode", function () {
      document.body.style.cursor = 'pointer';
    });

    networkInstance.current.on("blurNode", function () {
      document.body.style.cursor = 'default';
    });

    // Wait for stabilization then fit the entire graph in view
    networkInstance.current.on("stabilizationIterationsDone", function () {
      setTimeout(() => {
        if (networkInstance.current) {
          // Fit the entire network in the viewport
          networkInstance.current.fit({
            animation: {
              duration: 1000,
              easingFunction: 'easeInOutQuad'
            }
          });
        }
      }, 100);
    });

    // Trigger stabilization
    networkInstance.current.stabilize();
  };

  // Filter variables based on search
  const filteredVariables = searchTerm.length >= 2
    ? variables.filter(v => 
        v.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (v.label || '').toLowerCase().includes(searchTerm.toLowerCase())
      )
    : variables;

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'row', 
      height: '100vh',
      width: '100vw',
      backgroundColor: PolicyEngineTheme.colors.BLUE_98,
      overflow: 'hidden'
    }}>
      {/* Modern Sidebar */}
      <div style={{ 
        width: '380px',
        flexShrink: 0,
        backgroundColor: PolicyEngineTheme.colors.WHITE,
        borderRight: `2px solid ${PolicyEngineTheme.colors.BLUE_95}`,
        boxShadow: '4px 0 12px rgba(0,0,0,0.05)',
        overflowY: 'auto',
        height: '100vh',
        marginLeft: '16px'
      }}>
        <div style={{ padding: '20px 24px' }}>
          {/* Header with gradient */}
          <div className="mb-6" style={{
            padding: '24px',
            background: `linear-gradient(135deg, ${PolicyEngineTheme.colors.BLUE_PRIMARY} 0%, ${PolicyEngineTheme.colors.TEAL_ACCENT} 100%)`,
            borderRadius: '12px',
            boxShadow: '0 4px 16px rgba(44, 100, 150, 0.3)'
          }}>
            <div>
              <h1 className="text-xl font-bold text-white">
                PolicyEngine Flowchart
              </h1>
              <p className="text-xs mt-1" style={{ color: PolicyEngineTheme.colors.BLUE_98, opacity: 0.95 }}>
                Visualize variable dependencies
              </p>
              
              {/* Country Selector */}
              <div className="mt-3">
                <select 
                  value={selectedCountry}
                  onChange={(e) => {
                    setSelectedCountry(e.target.value);
                    setSelectedVariable('');
                    setSearchTerm('');
                    setError('');
                    setGraphData(null);
                  }}
                  className="px-3 py-1 text-sm rounded-md"
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    color: PolicyEngineTheme.colors.DARKEST_BLUE,
                    border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`,
                    outline: 'none',
                    cursor: 'pointer'
                  }}
                >
                  <option value="US">🇺🇸 United States ({variableCount > 0 ? variableCount.toLocaleString() : '...'} variables)</option>
                  <option value="UK">🇬🇧 United Kingdom ({selectedCountry === 'UK' && variableCount > 0 ? variableCount.toLocaleString() : '670'} variables)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Enhanced Search */}
          <div className="mb-5 relative" ref={searchContainerRef}>
            <label className="block text-sm font-semibold mb-2" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
              Search Variables
            </label>
            <div className="relative">
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 pointer-events-none" 
                   style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>
                <SearchIcon />
              </div>
              <input
                type="text"
                className="w-full pl-10 pr-3 py-3 text-sm rounded-lg focus:outline-none transition-all"
                style={{
                  border: `2px solid ${PolicyEngineTheme.colors.BLUE_95}`,
                  backgroundColor: PolicyEngineTheme.colors.WHITE,
                  boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.05)'
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = PolicyEngineTheme.colors.TEAL_ACCENT;
                  e.currentTarget.style.boxShadow = `0 0 0 3px ${PolicyEngineTheme.colors.TEAL_LIGHT}`;
                  if (searchTerm.length >= 2) setShowSearchResults(true);
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = PolicyEngineTheme.colors.BLUE_95;
                  e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(0,0,0,0.05)';
                }}
                placeholder="Type variable name (e.g., household_income)..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  searchVariables(e.target.value);
                }}
              />
            </div>
            
            {/* Enhanced Dropdown */}
            {showSearchResults && searchTerm.length >= 2 && (
              <div className="absolute z-10 w-full mt-2 bg-white rounded-lg shadow-xl max-h-64 overflow-y-auto" style={{
                border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`
              }}>
                {filteredVariables.slice(0, 5).map(v => (
                  <div
                    key={v.name}
                    className="px-4 py-3 cursor-pointer transition-all text-sm"
                    style={{
                      borderBottom: `1px solid ${PolicyEngineTheme.colors.BLUE_98}`
                    }}
                    onClick={() => selectVariable(v.name)}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = PolicyEngineTheme.colors.TEAL_LIGHT;
                      e.currentTarget.style.paddingLeft = '20px';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                      e.currentTarget.style.paddingLeft = '16px';
                    }}
                  >
                    <div className="font-mono font-semibold" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                      {v.name}
                    </div>
                  </div>
                ))}
                {filteredVariables.length === 0 && (
                  <div className="px-4 py-3 text-sm" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>
                    No variables found matching "{searchTerm}"
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Selected Variable Card */}
          {selectedVariable && (
            <div className="mb-5 p-4 rounded-lg" style={{
              backgroundColor: PolicyEngineTheme.colors.TEAL_LIGHT,
              border: `2px solid ${PolicyEngineTheme.colors.TEAL_ACCENT}`,
              animation: 'slideIn 0.3s ease-out'
            }}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-medium mb-1" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>
                    Selected Variable ({selectedCountry})
                  </div>
                  <div className="font-mono text-sm font-bold" style={{ color: PolicyEngineTheme.colors.TEAL_PRESSED }}>
                    {selectedVariable}
                  </div>
                </div>
                <button
                  onClick={() => {
                    setSelectedVariable('');
                    setSearchTerm('');
                    loadVariables();
                  }}
                  className="p-2 rounded-md transition-all hover:scale-110"
                  style={{ 
                    color: PolicyEngineTheme.colors.TEAL_PRESSED,
                    backgroundColor: PolicyEngineTheme.colors.WHITE,
                    border: `1px solid ${PolicyEngineTheme.colors.TEAL_ACCENT}`
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = PolicyEngineTheme.colors.TEAL_ACCENT;
                    e.currentTarget.style.color = PolicyEngineTheme.colors.WHITE;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = PolicyEngineTheme.colors.WHITE;
                    e.currentTarget.style.color = PolicyEngineTheme.colors.TEAL_PRESSED;
                  }}
                >
                  <ClearIcon />
                </button>
              </div>
            </div>
          )}

          {/* Advanced Options with better styling */}
          <div className="mb-5 rounded-lg overflow-hidden" style={{
            backgroundColor: PolicyEngineTheme.colors.BLUE_98,
            border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`
          }}>
            <button
              onClick={() => setDetailsOpen(!detailsOpen)}
              className="w-full px-4 py-3 text-sm font-semibold flex items-center justify-between transition-all"
              style={{ 
                color: PolicyEngineTheme.colors.DARKEST_BLUE,
                backgroundColor: detailsOpen ? PolicyEngineTheme.colors.BLUE_95 : 'transparent'
              }}
            >
              <span>⚙️ Advanced Options</span>
              <ChevronIcon open={detailsOpen} />
            </button>
            
            {detailsOpen && (
              <div className="p-4 space-y-4" style={{ animation: 'slideDown 0.2s ease-out' }}>
                {/* Max Depth with visual indicator */}
                <div>
                  <label className="block text-xs font-medium mb-2" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                    Max Depth: <span className="font-bold text-sm">{maxDepth}</span>
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="20"
                    value={maxDepth}
                    onChange={(e) => setMaxDepth(Number(e.target.value))}
                    className="w-full"
                    style={{ accentColor: PolicyEngineTheme.colors.TEAL_ACCENT }}
                  />
                  <div className="flex justify-between text-xs mt-1" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>
                    <span>1</span>
                    <span>20</span>
                  </div>
                </div>

                {/* Styled Checkboxes */}
                <div className="space-y-2">
                  <label className="flex items-center text-xs cursor-pointer p-2 rounded hover:bg-white transition-colors">
                    <input
                      type="checkbox"
                      checked={expandAddsSubtracts}
                      onChange={(e) => setExpandAddsSubtracts(e.target.checked)}
                      className="mr-2"
                      style={{ accentColor: PolicyEngineTheme.colors.TEAL_ACCENT }}
                    />
                    <span style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                      Expand Adds/Subtracts
                    </span>
                  </label>

                  <label className="flex items-center text-xs cursor-pointer p-2 rounded hover:bg-white transition-colors">
                    <input
                      type="checkbox"
                      checked={showLabels}
                      onChange={(e) => setShowLabels(e.target.checked)}
                      className="mr-2"
                      style={{ accentColor: PolicyEngineTheme.colors.TEAL_ACCENT }}
                    />
                    <span style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                      Show Labels
                    </span>
                  </label>

                  <label className="flex items-center text-xs cursor-pointer p-2 rounded hover:bg-white transition-colors">
                    <input
                      type="checkbox"
                      checked={showParameters}
                      onChange={(e) => setShowParameters(e.target.checked)}
                      className="mr-2"
                      style={{ accentColor: PolicyEngineTheme.colors.TEAL_ACCENT }}
                    />
                    <span style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                      Show Parameters
                    </span>
                  </label>
                </div>

                {/* Parameter Options */}
                {showParameters && (
                  <>
                    <div>
                      <label className="block text-xs font-medium mb-1" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                        Parameter Detail Level
                      </label>
                      <select
                        value={paramDetailLevel}
                        onChange={(e) => setParamDetailLevel(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-md"
                        style={{
                          border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`,
                          backgroundColor: PolicyEngineTheme.colors.WHITE
                        }}
                      >
                        <option value="Minimal">Minimal</option>
                        <option value="Summary">Summary</option>
                        <option value="Full">Full</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium mb-1" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                        Don't Show Parameters For:
                      </label>
                      <textarea
                        className="w-full px-3 py-2 text-xs rounded-md"
                        style={{
                          border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`,
                          backgroundColor: PolicyEngineTheme.colors.WHITE,
                          resize: 'vertical'
                        }}
                        rows={2}
                        placeholder="Enter variable names, one per line"
                        value={noParamsList}
                        onChange={(e) => setNoParamsList(e.target.value)}
                      />
                    </div>
                  </>
                )}

                {/* Stop Variables */}
                <div>
                  <label className="block text-xs font-medium mb-1" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                    Stop Variables (optional):
                  </label>
                  <textarea
                    className="w-full px-3 py-2 text-xs rounded-md"
                    style={{
                      border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`,
                      backgroundColor: PolicyEngineTheme.colors.WHITE,
                      resize: 'vertical'
                    }}
                    rows={3}
                    placeholder="employment_income&#10;self_employment_income&#10;pension_income"
                    value={stopVariables}
                    onChange={(e) => setStopVariables(e.target.value)}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Enhanced Generate Button */}
          <button
            onClick={generateFlowchart}
            disabled={loading || !selectedVariable}
            className="w-full py-3 px-4 rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2"
            style={{ 
              backgroundColor: loading || !selectedVariable ? PolicyEngineTheme.colors.MEDIUM_LIGHT_GRAY : PolicyEngineTheme.colors.BLUE_PRIMARY,
              color: PolicyEngineTheme.colors.WHITE,
              boxShadow: loading || !selectedVariable ? 'none' : '0 4px 12px rgba(44, 100, 150, 0.4)',
              transform: 'translateY(0)',
              cursor: loading || !selectedVariable ? 'not-allowed' : 'pointer'
            }}
            onMouseEnter={(e) => {
              if (!loading && selectedVariable) {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(44, 100, 150, 0.5)';
              }
            }}
            onMouseLeave={(e) => {
              if (!loading && selectedVariable) {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(44, 100, 150, 0.4)';
              }
            }}
          >
            {loading ? (
              <>
                <LoadingSpinner />
                <span>Generating...</span>
              </>
            ) : (
              <span>Generate Flowchart</span>
            )}
          </button>

          {/* Error Display */}
          {error && (
            <div className="mt-4 p-3 rounded-lg text-xs flex items-start gap-2" style={{
              backgroundColor: '#FEF2F2',
              border: `1px solid ${PolicyEngineTheme.colors.DARK_RED}`,
              color: PolicyEngineTheme.colors.DARK_RED
            }}>
              <span>⚠️</span>
              <div>
                <strong>Error:</strong> {error}
              </div>
            </div>
          )}


          {/* Graph Stats with better design */}
          {graphData && (
            <div className="mt-4 p-3 rounded-lg" style={{
              backgroundColor: PolicyEngineTheme.colors.TEAL_LIGHT,
              border: `1px solid ${PolicyEngineTheme.colors.TEAL_ACCENT}`
            }}>
              <div className="text-xs font-semibold mb-3" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                Graph Statistics
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="p-3 rounded text-center" style={{
                  backgroundColor: PolicyEngineTheme.colors.WHITE,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ color: PolicyEngineTheme.colors.BLUE_PRIMARY, fontSize: '20px', fontWeight: 'bold' }}>
                    {graphData.nodes.length}
                  </div>
                  <div style={{ color: PolicyEngineTheme.colors.DARK_GRAY, fontSize: '11px' }}>Nodes</div>
                </div>
                <div className="p-3 rounded text-center" style={{
                  backgroundColor: PolicyEngineTheme.colors.WHITE,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ color: PolicyEngineTheme.colors.TEAL_ACCENT, fontSize: '20px', fontWeight: 'bold' }}>
                    {graphData.edges.length}
                  </div>
                  <div style={{ color: PolicyEngineTheme.colors.DARK_GRAY, fontSize: '11px' }}>Edges</div>
                </div>
              </div>
            </div>
          )}

          {/* Legend Section */}
          {graphData && (
            <div className="mt-4 p-4 rounded-lg" style={{
              backgroundColor: PolicyEngineTheme.colors.WHITE,
              border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`,
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
            }}>
              <h3 
                className="text-sm font-semibold cursor-pointer flex items-center gap-1"
                onClick={() => setLegendExpanded(!legendExpanded)}
                style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE, userSelect: 'none', margin: 0 }}
              >
                Legend
                <svg
                  className={`inline-block transition-transform duration-200 ${legendExpanded ? 'rotate-180' : ''}`}
                  width="10"
                  height="10"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke={PolicyEngineTheme.colors.DARK_GRAY}
                  strokeWidth="2"
                  style={{ marginLeft: '2px' }}
                >
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </h3>
              
              {legendExpanded && (
                <div className="mt-3 space-y-0">
                  {/* Node Types */}
                  <div>
                    <p className="text-xs font-semibold mb-2" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                      Nodes
                    </p>
                    <div className="space-y-2" style={{ paddingLeft: '12px' }}>
                      <div className="flex items-center gap-3">
                        <div style={{ 
                          width: '14px',
                          height: '14px',
                          borderRadius: '50%',
                          backgroundColor: PolicyEngineTheme.colors.TEAL_ACCENT,
                          flexShrink: 0
                        }}></div>
                        <span className="text-xs" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>Root</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div style={{ 
                          width: '14px',
                          height: '14px',
                          borderRadius: '50%',
                          backgroundColor: PolicyEngineTheme.colors.BLUE_PRIMARY,
                          flexShrink: 0
                        }}></div>
                        <span className="text-xs" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>Dependency</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div style={{ 
                          width: '14px',
                          height: '14px',
                          borderRadius: '50%',
                          backgroundColor: PolicyEngineTheme.colors.DARK_RED,
                          flexShrink: 0
                        }}></div>
                        <span className="text-xs" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>Stop</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div style={{ 
                          width: '14px',
                          height: '14px',
                          borderRadius: '50%',
                          backgroundColor: '#8B4B9B',
                          flexShrink: 0
                        }}></div>
                        <span className="text-xs" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>Defined For</span>
                      </div>
                    </div>
                  </div>

                  {/* Divider */}
                  <div style={{ 
                    borderTop: `1px dashed ${PolicyEngineTheme.colors.BLUE_95}`,
                    marginTop: '6px',
                    marginBottom: '6px'
                  }}></div>

                  {/* Edge Types */}
                  <div>
                    <p className="text-xs font-semibold mb-2" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                      Edges
                    </p>
                    <div className="space-y-2" style={{ paddingLeft: '12px' }}>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold" style={{ color: PolicyEngineTheme.colors.GREEN, minWidth: '65px' }}>+ (green)</span>
                        <span className="text-xs" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>Addition</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold" style={{ color: PolicyEngineTheme.colors.DARK_RED, minWidth: '65px' }}>- (red)</span>
                        <span className="text-xs" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>Subtraction</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div style={{ minWidth: '65px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <div className="w-8 h-0.5" style={{ backgroundColor: PolicyEngineTheme.colors.GRAY }}></div>
                        </div>
                        <span className="text-xs" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>Reference</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Graph Container with better styling */}
      <div style={{ 
        flex: 1,
        padding: '24px',
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden',
        position: 'relative'
      }}>
        <div ref={networkContainer} style={{
          width: '100%',
          height: '100%',
          backgroundColor: PolicyEngineTheme.colors.WHITE,
          boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
          border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`,
          borderRadius: '12px',
          flex: 1
        }}></div>
        
      </div>

    </div>
  );
}

export default App;