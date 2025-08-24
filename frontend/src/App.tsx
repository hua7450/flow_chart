import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { Network } from 'vis-network/standalone';
import axios from 'axios';

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

  // Load variables on mount
  useEffect(() => {
    loadVariables();
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
    if (query.length < 2) return;
    
    try {
      const response = await axios.get(`${API_BASE}/search`, {
        params: { q: query }
      });
      if (response.data.success) {
        setVariables(response.data.results);
      }
    } catch (err) {
      console.error('Search failed:', err);
    }
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
        widthConstraint: { minimum: 120, maximum: 250 },
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
        tooltipDelay: 100,
        zoomView: true,
        dragView: true
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
    <div className="flex flex-row h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-80 bg-white shadow-lg p-4 overflow-y-auto flex-shrink-0 border-r border-gray-200">
        <h1 className="text-xl font-bold mb-4 text-gray-800">
          PolicyEngine Flowchart
        </h1>

        {/* Variable Selection */}
        <div className="mb-4">
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Search Variables
          </label>
          <input
            type="text"
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Type to search..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              if (e.target.value.length >= 2) {
                searchVariables(e.target.value);
              }
            }}
          />
        </div>

        <div className="mb-4">
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Or select from all variables:
          </label>
          <select
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={selectedVariable}
            onChange={(e) => setSelectedVariable(e.target.value)}
            size={8}
          >
            <option value="">Select a variable...</option>
            {filteredVariables.map(v => (
              <option key={v.name} value={v.name}>
                {v.name} {v.hasParameters && '📊'}
              </option>
            ))}
          </select>
        </div>

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
          className="w-full bg-blue-600 text-white py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
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
          <div className="mt-3 p-2 bg-green-100 border border-green-400 text-green-700 rounded text-xs">
            ✅ Graph: {graphData.nodes.length} nodes, {graphData.edges.length} edges
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 h-full">
        <div className="bg-white m-2 rounded-lg shadow-lg flex-1 flex flex-col min-h-0">
          <h2 className="text-lg font-semibold p-4 pb-2 text-gray-800 flex-shrink-0">
            Dependency Flowchart
          </h2>
          <div ref={networkContainer} className="flex-1 min-h-0 mx-4 mb-4 border border-gray-200 rounded" />
        </div>
      </div>
    </div>
  );
}

export default App;