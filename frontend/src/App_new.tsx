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

const API_BASE = 'http://localhost:5001/api';

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

const GraphIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="3"></circle>
    <line x1="12" y1="1" x2="12" y2="9"></line>
    <line x1="12" y1="15" x2="12" y2="23"></line>
    <line x1="4.22" y1="4.22" x2="9.17" y2="9.17"></line>
    <line x1="14.83" y1="14.83" x2="19.78" y2="19.78"></line>
    <line x1="1" y1="12" x2="9" y2="12"></line>
    <line x1="15" y1="12" x2="23" y2="12"></line>
    <line x1="4.22" y1="19.78" x2="9.17" y2="14.83"></line>
    <line x1="14.83" y1="9.17" x2="19.78" y2="4.22"></line>
  </svg>
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
  
  // Controls
  const [maxDepth, setMaxDepth] = useState<number>(10);
  const [expandAddsSubtracts, setExpandAddsSubtracts] = useState<boolean>(true);
  const [showLabels, setShowLabels] = useState<boolean>(true);
  const [showParameters, setShowParameters] = useState<boolean>(true);
  const [paramDetailLevel, setParamDetailLevel] = useState<string>('Summary');
  const [stopVariables, setStopVariables] = useState<string>('');
  const [noParamsList, setNoParamsList] = useState<string>('');
  
  const networkContainer = useRef<HTMLDivElement>(null);
  const networkInstance = useRef<Network | null>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);
  const [filteredVariables, setFilteredVariables] = useState<Variable[]>([]);

  // Load variables on mount
  useEffect(() => {
    loadVariables();
  }, []);

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
      const response = await axios.get(`${API_BASE}/variables`);
      if (response.data.success) {
        setVariables(response.data.variables);
      }
    } catch (err) {
      setError('Failed to load variables');
      console.error(err);
    }
  };

  const searchVariables = async (query: string) => {
    if (query.length < 2) {
      setShowSearchResults(false);
      setFilteredVariables([]);
      return;
    }
    
    try {
      const response = await axios.get(`${API_BASE}/search`, {
        params: { q: query }
      });
      if (response.data.success) {
        setFilteredVariables(response.data.results);
        setShowSearchResults(true);
      }
    } catch (err) {
      console.error('Search error:', err);
    }
  };

  const selectVariable = (varName: string) => {
    setSelectedVariable(varName);
    setSearchTerm('');
    setShowSearchResults(false);
    setError('');
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
        maxDepth,
        expandAddsSubtracts,
        showParameters,
        paramDetailLevel,
        stopVariables: stopVariables.split(',').map(v => v.trim()).filter(v => v),
        noParamsList: noParamsList.split(',').map(v => v.trim()).filter(v => v),
        showLabels
      });

      if (response.data.success) {
        setGraphData(response.data.graph);
        renderGraph(response.data.graph);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to generate flowchart');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const renderGraph = (data: GraphData) => {
    if (!networkContainer.current) return;

    // Destroy existing network
    if (networkInstance.current) {
      networkInstance.current.destroy();
    }

    const options = {
      layout: {
        hierarchical: {
          direction: 'UD',
          sortMethod: 'directed',
          levelSeparation: 150,
          nodeSpacing: 200,
          treeSpacing: 250,
          blockShifting: true,
          edgeMinimization: true,
          parentCentralization: true
        }
      },
      physics: {
        enabled: false
      },
      nodes: {
        borderWidth: 2,
        borderWidthSelected: 3,
        font: {
          size: 14,
          face: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
        },
        shape: 'box',
        margin: { top: 10, right: 10, bottom: 10, left: 10 },
        widthConstraint: {
          maximum: 200
        },
        shadow: {
          enabled: true,
          color: 'rgba(0,0,0,0.1)',
          size: 10,
          x: 0,
          y: 2
        }
      },
      edges: {
        width: 2,
        smooth: {
          enabled: true,
          type: 'cubicBezier',
          roundness: 0.5
        },
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
        navigationButtons: true,
        keyboard: {
          enabled: true,
          speed: { x: 10, y: 10, zoom: 0.02 }
        }
      }
    };

    networkInstance.current = new Network(
      networkContainer.current,
      { nodes: data.nodes, edges: data.edges },
      options
    );

    // Add hover effects
    networkInstance.current.on("hoverNode", function (params) {
      document.body.style.cursor = 'pointer';
    });

    networkInstance.current.on("blurNode", function (params) {
      document.body.style.cursor = 'default';
    });

    // Center on the target node
    setTimeout(() => {
      const targetNode = data.nodes.find(n => n.level === 0);
      if (targetNode && networkInstance.current) {
        networkInstance.current.focus(targetNode.id, {
          scale: 1,
          animation: {
            duration: 1000,
            easingFunction: 'easeInOutQuad'
          }
        });
      }
    }, 100);
  };

  return (
    <div className="h-screen" style={{ display: 'flex', flexDirection: 'row', backgroundColor: PolicyEngineTheme.colors.BLUE_98 }}>
      {/* Sidebar */}
      <div className="overflow-y-auto" style={{ 
        width: '360px', 
        flexShrink: 0,
        backgroundColor: PolicyEngineTheme.colors.WHITE,
        borderRight: `2px solid ${PolicyEngineTheme.colors.BLUE_95}`,
        boxShadow: '4px 0 12px rgba(0,0,0,0.05)'
      }}>
        <div className="p-5">
          {/* Header */}
          <div className="mb-6" style={{
            padding: '20px',
            background: `linear-gradient(135deg, ${PolicyEngineTheme.colors.BLUE_PRIMARY} 0%, ${PolicyEngineTheme.colors.TEAL_ACCENT} 100%)`,
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(44, 100, 150, 0.25)'
          }}>
            <div className="flex items-center gap-3">
              <div style={{ color: PolicyEngineTheme.colors.WHITE }}>
                <GraphIcon />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">
                  PolicyEngine Flowchart
                </h1>
                <p className="text-xs mt-1" style={{ color: PolicyEngineTheme.colors.BLUE_98, opacity: 0.9 }}>
                  Visualize variable dependencies
                </p>
              </div>
            </div>
          </div>

          {/* Variable Search */}
          <div className="mb-5 relative" ref={searchContainerRef}>
            <label className="block text-sm font-semibold mb-2" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
              Search Variables
            </label>
            <div className="relative">
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>
                <SearchIcon />
              </div>
              <input
                type="text"
                className="w-full pl-9 pr-3 py-2.5 text-sm rounded-lg focus:outline-none transition-all"
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
                placeholder="Type variable name..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  searchVariables(e.target.value);
                }}
              />
            </div>
            
            {/* Search Results Dropdown */}
            {showSearchResults && searchTerm.length >= 2 && (
              <div className="absolute z-10 w-full mt-2 bg-white rounded-lg shadow-lg max-h-60 overflow-y-auto" style={{
                border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`
              }}>
                {filteredVariables.slice(0, 10).map(v => (
                  <div
                    key={v.name}
                    className="px-3 py-2 cursor-pointer text-sm font-mono transition-colors"
                    style={{
                      borderBottom: `1px solid ${PolicyEngineTheme.colors.BLUE_98}`
                    }}
                    onClick={() => selectVariable(v.name)}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = PolicyEngineTheme.colors.TEAL_LIGHT;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <div style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>{v.name}</div>
                    {v.label && (
                      <div className="text-xs mt-0.5" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>
                        {v.label}
                      </div>
                    )}
                  </div>
                ))}
                {filteredVariables.length === 0 && (
                  <div className="px-3 py-2 text-sm" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>
                    No variables found
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Selected Variable Display */}
          {selectedVariable && (
            <div className="mb-5 p-3 rounded-lg" style={{
              backgroundColor: PolicyEngineTheme.colors.TEAL_LIGHT,
              border: `1px solid ${PolicyEngineTheme.colors.TEAL_ACCENT}`
            }}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-medium mb-1" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>
                    Selected Variable
                  </div>
                  <div className="font-mono text-sm font-bold" style={{ color: PolicyEngineTheme.colors.TEAL_PRESSED }}>
                    {selectedVariable}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedVariable('')}
                  className="p-1.5 rounded-md transition-all"
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

          {/* Advanced Options */}
          <div className="mb-5 rounded-lg overflow-hidden" style={{
            backgroundColor: PolicyEngineTheme.colors.BLUE_98,
            border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`
          }}>
            <button
              onClick={() => setDetailsOpen(!detailsOpen)}
              className="w-full px-4 py-3 text-sm font-semibold flex items-center justify-between transition-colors"
              style={{ 
                color: PolicyEngineTheme.colors.DARKEST_BLUE,
                backgroundColor: detailsOpen ? PolicyEngineTheme.colors.BLUE_95 : 'transparent'
              }}
            >
              <span>Advanced Options</span>
              <ChevronIcon open={detailsOpen} />
            </button>
            
            {detailsOpen && (
              <div className="p-4 space-y-4">
                {/* Max Depth */}
                <div>
                  <label className="block text-xs font-medium mb-2" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                    Max Depth: {maxDepth}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="20"
                    value={maxDepth}
                    onChange={(e) => setMaxDepth(parseInt(e.target.value))}
                    className="w-full"
                    style={{ accentColor: PolicyEngineTheme.colors.TEAL_ACCENT }}
                  />
                </div>

                {/* Checkboxes */}
                <div className="space-y-2">
                  <label className="flex items-center text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={expandAddsSubtracts}
                      onChange={(e) => setExpandAddsSubtracts(e.target.checked)}
                      className="mr-2"
                      style={{ accentColor: PolicyEngineTheme.colors.TEAL_ACCENT }}
                    />
                    <span style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                      Expand adds/subtracts
                    </span>
                  </label>

                  <label className="flex items-center text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showLabels}
                      onChange={(e) => setShowLabels(e.target.checked)}
                      className="mr-2"
                      style={{ accentColor: PolicyEngineTheme.colors.TEAL_ACCENT }}
                    />
                    <span style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                      Show labels
                    </span>
                  </label>

                  <label className="flex items-center text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showParameters}
                      onChange={(e) => setShowParameters(e.target.checked)}
                      className="mr-2"
                      style={{ accentColor: PolicyEngineTheme.colors.TEAL_ACCENT }}
                    />
                    <span style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                      Show parameters
                    </span>
                  </label>
                </div>

                {/* Parameter Detail Level */}
                {showParameters && (
                  <div>
                    <label className="block text-xs font-medium mb-1" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                      Parameter Detail Level
                    </label>
                    <select
                      value={paramDetailLevel}
                      onChange={(e) => setParamDetailLevel(e.target.value)}
                      className="w-full px-2 py-1.5 text-xs rounded-md"
                      style={{
                        border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`,
                        backgroundColor: PolicyEngineTheme.colors.WHITE
                      }}
                    >
                      <option value="Summary">Summary</option>
                      <option value="Latest 5 values">Latest 5 values</option>
                      <option value="All values">All values</option>
                    </select>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Generate Button */}
          <button
            onClick={generateFlowchart}
            disabled={loading || !selectedVariable}
            className="w-full py-3 px-4 rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2"
            style={{ 
              backgroundColor: loading || !selectedVariable ? PolicyEngineTheme.colors.MEDIUM_LIGHT_GRAY : PolicyEngineTheme.colors.BLUE_PRIMARY,
              color: PolicyEngineTheme.colors.WHITE,
              boxShadow: loading || !selectedVariable ? 'none' : '0 4px 8px rgba(44, 100, 150, 0.3)',
              transform: 'translateY(0)',
              cursor: loading || !selectedVariable ? 'not-allowed' : 'pointer'
            }}
            onMouseEnter={(e) => {
              if (!loading && selectedVariable) {
                e.currentTarget.style.backgroundColor = PolicyEngineTheme.colors.DARK_BLUE_HOVER;
                e.currentTarget.style.boxShadow = '0 6px 12px rgba(44, 100, 150, 0.4)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }
            }}
            onMouseLeave={(e) => {
              if (!loading && selectedVariable) {
                e.currentTarget.style.backgroundColor = PolicyEngineTheme.colors.BLUE_PRIMARY;
                e.currentTarget.style.boxShadow = '0 4px 8px rgba(44, 100, 150, 0.3)';
                e.currentTarget.style.transform = 'translateY(0)';
              }
            }}
          >
            {loading ? (
              <>
                <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                <span>Generating...</span>
              </>
            ) : (
              <>
                <GraphIcon />
                <span>Generate Flowchart</span>
              </>
            )}
          </button>

          {/* Error Display */}
          {error && (
            <div className="mt-4 p-3 rounded-lg text-xs" style={{
              backgroundColor: '#FEF2F2',
              border: `1px solid ${PolicyEngineTheme.colors.DARK_RED}`,
              color: PolicyEngineTheme.colors.DARK_RED
            }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {/* Legend Section */}
          {graphData && (
            <div className="mt-5 p-4 rounded-lg" style={{
              backgroundColor: PolicyEngineTheme.colors.BLUE_98,
              border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`
            }}>
              <h3 className="text-sm font-semibold mb-3" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                Legend
              </h3>
              
              <div className="space-y-2">
                {/* Node Types */}
                <div className="text-xs">
                  <div className="font-medium mb-1" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>
                    Node Types:
                  </div>
                  <div className="space-y-1 ml-2">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded" style={{ backgroundColor: PolicyEngineTheme.colors.TEAL_ACCENT }}></div>
                      <span>Target Variable</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded" style={{ backgroundColor: PolicyEngineTheme.colors.BLUE_LIGHT }}></div>
                      <span>Regular Variable</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded" style={{ 
                        backgroundColor: PolicyEngineTheme.colors.BLUE_98,
                        border: `2px solid ${PolicyEngineTheme.colors.DARK_RED}`
                      }}></div>
                      <span>Stop Variable</span>
                    </div>
                  </div>
                </div>

                {/* Edge Types */}
                <div className="text-xs">
                  <div className="font-medium mb-1" style={{ color: PolicyEngineTheme.colors.DARK_GRAY }}>
                    Arrow Types:
                  </div>
                  <div className="space-y-1 ml-2">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-0.5" style={{ backgroundColor: PolicyEngineTheme.colors.GRAY }}></div>
                      <span>Dependency</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-0.5" style={{ backgroundColor: PolicyEngineTheme.colors.GREEN }}></div>
                      <span>Addition (+)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-0.5" style={{ backgroundColor: PolicyEngineTheme.colors.DARK_RED }}></div>
                      <span>Subtraction (-)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Graph Stats */}
          {graphData && (
            <div className="mt-4 p-3 rounded-lg" style={{
              backgroundColor: PolicyEngineTheme.colors.BLUE_98,
              border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`
            }}>
              <div className="text-xs font-semibold mb-2" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
                Graph Statistics
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2 rounded text-center" style={{
                  backgroundColor: PolicyEngineTheme.colors.WHITE
                }}>
                  <div style={{ color: PolicyEngineTheme.colors.BLUE_PRIMARY, fontSize: '18px', fontWeight: 'bold' }}>
                    {graphData.nodes.length}
                  </div>
                  <div style={{ color: PolicyEngineTheme.colors.DARK_GRAY, fontSize: '10px' }}>Nodes</div>
                </div>
                <div className="p-2 rounded text-center" style={{
                  backgroundColor: PolicyEngineTheme.colors.WHITE
                }}>
                  <div style={{ color: PolicyEngineTheme.colors.TEAL_ACCENT, fontSize: '18px', fontWeight: 'bold' }}>
                    {graphData.edges.length}
                  </div>
                  <div style={{ color: PolicyEngineTheme.colors.DARK_GRAY, fontSize: '10px' }}>Edges</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Graph Container */}
      <div className="flex-1 p-6">
        <div ref={networkContainer} className="w-full h-full rounded-xl" style={{
          backgroundColor: PolicyEngineTheme.colors.WHITE,
          boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
          border: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`
        }}></div>
      </div>
    </div>
  );
}

export default App;