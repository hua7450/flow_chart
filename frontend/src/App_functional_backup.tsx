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

function App() {
  const [variables, setVariables] = useState<Variable[]>([]);
  const [selectedVariable, setSelectedVariable] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [showSearchResults, setShowSearchResults] = useState<boolean>(false);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  
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
      return;
    }
    
    try {
      const response = await axios.get(`${API_BASE}/search`, {
        params: { q: query }
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
    // Reload all variables to reset the list
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

    const options = {
      layout: {
        hierarchical: {
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed',
          nodeSpacing: 200,
          levelSeparation: 100,
          treeSpacing: 150,
          blockShifting: true,
          edgeMinimization: true
        }
      },
      autoResize: true,
      physics: {
        enabled: false
      },
      nodes: {
        borderWidth: 2,
        borderWidthSelected: 4,
        margin: { top: 10, right: 10, bottom: 10, left: 10 },
        widthConstraint: { maximum: 250 },
        heightConstraint: { minimum: 40 },
        font: {
          size: 14,
          face: 'Arial, sans-serif'
        },
        shape: 'box'
      },
      edges: {
        smooth: {
          enabled: true,
          type: 'cubicBezier',
          roundness: 0.4
        },
        width: 2,
        arrows: {
          to: {
            enabled: true,
            scaleFactor: 1
          }
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 300,
        hideEdgesOnDrag: false,
        hideNodesOnDrag: false,
        zoomView: true,
        dragView: true
      },
      configure: {
        enabled: false
      }
    };

    // Destroy existing network if it exists
    if (networkInstance.current) {
      networkInstance.current.destroy();
    }

    // Create new network
    networkInstance.current = new Network(
      networkContainer.current,
      { nodes: data.nodes, edges: data.edges },
      options
    );

    // Fit the network to the viewport after rendering
    networkInstance.current.once('stabilized', () => {
      networkInstance.current?.fit({
        animation: {
          duration: 500,
          easingFunction: 'easeInOutQuad'
        }
      });
    });
  };

  // Filter variables based on search
  const filteredVariables = searchTerm.length >= 2
    ? variables.filter(v => 
        v.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        v.label.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : variables;

  return (
    <div className="h-screen" style={{ display: 'flex', flexDirection: 'row', backgroundColor: PolicyEngineTheme.colors.BLUE_98 }}>
      {/* Sidebar */}
      <div className="shadow p-3 overflow-y-auto" style={{ 
        width: '300px', 
        flexShrink: 0,
        backgroundColor: PolicyEngineTheme.colors.WHITE,
        borderRight: `1px solid ${PolicyEngineTheme.colors.MEDIUM_DARK_GRAY}`
      }}>
        <h1 className="text-xl font-bold mb-4" style={{ color: PolicyEngineTheme.colors.DARKEST_BLUE }}>
          PolicyEngine Flowchart
        </h1>

        {/* Variable Selection */}
        <div className="mb-4 relative" ref={searchContainerRef}>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            {selectedVariable ? `Selected: ${selectedVariable}` : 'Or search all variables:'}
          </label>
          <input
            type="text"
            className="w-full px-2 py-1 text-xs rounded focus:outline-none"
            style={{
              border: `1px solid ${PolicyEngineTheme.colors.MEDIUM_DARK_GRAY}`
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = PolicyEngineTheme.colors.TEAL_ACCENT;
              if (searchTerm.length >= 2) setShowSearchResults(true);
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = PolicyEngineTheme.colors.MEDIUM_DARK_GRAY;
            }}
            placeholder={selectedVariable ? selectedVariable : "Type variable name..."}
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              searchVariables(e.target.value);
            }}
          />
          
          {/* Search Results Dropdown */}
          {showSearchResults && searchTerm.length >= 2 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded shadow-sm max-h-48 overflow-y-auto">
              {filteredVariables.slice(0, 6).map(v => (
                <div
                  key={v.name}
                  className="px-2 py-1 cursor-pointer hover:bg-gray-100 text-xs font-mono border-b border-gray-100 last:border-b-0"
                  onClick={() => selectVariable(v.name)}
                >
                  {v.name}
                </div>
              ))}
              {filteredVariables.length === 0 && (
                <div className="px-2 py-1 text-xs text-gray-500">No variables found</div>
              )}
            </div>
          )}
        </div>

        {selectedVariable && (
          <div className="mb-4">
            <button
              onClick={() => {
                setSelectedVariable('');
                setSearchTerm('');
                setShowSearchResults(false);
                loadVariables();
              }}
              className="text-xs transition-colors"
              style={{ color: PolicyEngineTheme.colors.TEAL_ACCENT }}
              onMouseEnter={(e) => e.currentTarget.style.color = PolicyEngineTheme.colors.TEAL_PRESSED}
              onMouseLeave={(e) => e.currentTarget.style.color = PolicyEngineTheme.colors.TEAL_ACCENT}
            >
              Clear selection
            </button>
          </div>
        )}

        {/* Advanced Options */}
        <details className="mb-4">
          <summary className="cursor-pointer text-sm font-medium text-gray-700 mb-2">
            Advanced Options
          </summary>
          
          <div className="space-y-3 mt-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Maximum Depth: {maxDepth}
              </label>
              <input
                type="range"
                min="1"
                max="20"
                value={maxDepth}
                onChange={(e) => setMaxDepth(Number(e.target.value))}
                className="w-full h-1"
              />
            </div>

            <div>
              <label className="flex items-center text-xs">
                <input
                  type="checkbox"
                  checked={expandAddsSubtracts}
                  onChange={(e) => setExpandAddsSubtracts(e.target.checked)}
                  className="mr-1"
                />
                Expand Adds/Subtracts
              </label>
            </div>

            <div>
              <label className="flex items-center text-xs">
                <input
                  type="checkbox"
                  checked={showLabels}
                  onChange={(e) => setShowLabels(e.target.checked)}
                  className="mr-1"
                />
                Show Labels
              </label>
            </div>

            <div>
              <label className="flex items-center text-xs">
                <input
                  type="checkbox"
                  checked={showParameters}
                  onChange={(e) => setShowParameters(e.target.checked)}
                  className="mr-1"
                />
                Show Parameters
              </label>
            </div>

            {showParameters && (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Parameter Detail Level
                  </label>
                  <select
                    className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                    value={paramDetailLevel}
                    onChange={(e) => setParamDetailLevel(e.target.value)}
                  >
                    <option value="Minimal">Minimal</option>
                    <option value="Summary">Summary</option>
                    <option value="Full">Full</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Don't Show Parameters For:
                  </label>
                  <textarea
                    className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                    rows={2}
                    placeholder="ca_riv_share_eligible&#10;ca_riv_share_electricity_emergency_payment"
                    value={noParamsList}
                    onChange={(e) => setNoParamsList(e.target.value)}
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Stop Variables (optional):
              </label>
              <textarea
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                rows={2}
                placeholder="employment_income&#10;self_employment_income&#10;pension_income"
                value={stopVariables}
                onChange={(e) => setStopVariables(e.target.value)}
              />
            </div>
          </div>
        </details>

        {/* Generate Button */}
        <button
          onClick={generateFlowchart}
          disabled={loading || !selectedVariable}
          className="w-full text-white py-2 rounded text-sm font-medium disabled:cursor-not-allowed transition-colors"
          style={{ 
            backgroundColor: loading || !selectedVariable ? PolicyEngineTheme.colors.MEDIUM_LIGHT_GRAY : PolicyEngineTheme.colors.BLUE_PRIMARY
          }}
          onMouseEnter={(e) => {
            if (!loading && selectedVariable) {
              e.currentTarget.style.backgroundColor = PolicyEngineTheme.colors.DARK_BLUE_HOVER;
            }
          }}
          onMouseLeave={(e) => {
            if (!loading && selectedVariable) {
              e.currentTarget.style.backgroundColor = PolicyEngineTheme.colors.BLUE_PRIMARY;
            }
          }}
        >
          {loading ? 'Generating...' : 'Generate Flowchart'}
        </button>

        {/* Error Display */}
        {error && (
          <div className="mt-3 p-2 bg-red-100 border border-red-400 text-red-700 rounded text-xs">
            {error}
          </div>
        )}

        {/* Graph Stats */}
        {graphData && (
          <div className="mt-3 p-2 rounded text-xs" style={{
            backgroundColor: PolicyEngineTheme.colors.TEAL_LIGHT,
            border: `1px solid ${PolicyEngineTheme.colors.TEAL_ACCENT}`,
            color: PolicyEngineTheme.colors.DARKEST_BLUE
          }}>
            ✅ Graph: {graphData.nodes.length} nodes, {graphData.edges.length} edges
          </div>
        )}
      </div>

      {/* Main Content */}
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        flexDirection: 'column', 
        minWidth: 0, 
        height: '100vh',
        backgroundColor: PolicyEngineTheme.colors.WHITE
      }}>
        <h2 className="text-lg font-semibold px-3 py-2" style={{ 
          flexShrink: 0,
          color: PolicyEngineTheme.colors.DARKEST_BLUE,
          borderBottom: `1px solid ${PolicyEngineTheme.colors.BLUE_95}`
        }}>
          Dependency Flowchart
        </h2>
        <div ref={networkContainer} style={{ flex: 1, minHeight: 0, width: '100%' }} />
      </div>
    </div>
  );
}

export default App;