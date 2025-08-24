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

// Suppress ResizeObserver errors (common with vis-network)
if (typeof window !== 'undefined') {
  window.addEventListener('error', (e) => {
    if (e.message === 'ResizeObserver loop completed with undelivered notifications.') {
      e.stopPropagation();
      e.preventDefault();
    }
  });
}

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
          nodeSpacing: 180,
          levelSeparation: 120,
          treeSpacing: 150,
          blockShifting: true,
          edgeMinimization: true
        }
      },
      physics: {
        enabled: false
      },
      nodes: {
        borderWidth: 2,
        borderWidthSelected: 4,
        margin: { top: 8, right: 8, bottom: 8, left: 8 },
        widthConstraint: { maximum: 180 },
        heightConstraint: { minimum: 35 }
      },
      edges: {
        smooth: {
          enabled: true,
          type: 'cubicBezier',
          roundness: 0.4
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100
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
  };

  // Filter variables based on search
  const filteredVariables = searchTerm.length >= 2
    ? variables.filter(v => 
        v.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        v.label.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : variables;

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-96 bg-white shadow-lg p-6 overflow-y-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-800">
          PolicyEngine Flowchart
        </h1>

        {/* Variable Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Search Variables
          </label>
          <input
            type="text"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Or select from all variables:
          </label>
          <select
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={selectedVariable}
            onChange={(e) => setSelectedVariable(e.target.value)}
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
        <details className="mb-6">
          <summary className="cursor-pointer font-medium text-gray-700 mb-3">
            Advanced Options
          </summary>
          
          <div className="space-y-4 mt-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Maximum Depth: {maxDepth}
              </label>
              <input
                type="range"
                min="1"
                max="20"
                value={maxDepth}
                onChange={(e) => setMaxDepth(Number(e.target.value))}
                className="w-full"
              />
            </div>

            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={expandAddsSubtracts}
                  onChange={(e) => setExpandAddsSubtracts(e.target.checked)}
                  className="mr-2"
                />
                Expand Adds/Subtracts
              </label>
            </div>

            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={showLabels}
                  onChange={(e) => setShowLabels(e.target.checked)}
                  className="mr-2"
                />
                Show Labels
              </label>
            </div>

            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={showParameters}
                  onChange={(e) => setShowParameters(e.target.checked)}
                  className="mr-2"
                />
                Show Parameters
              </label>
            </div>

            {showParameters && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Parameter Detail Level
                  </label>
                  <select
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={paramDetailLevel}
                    onChange={(e) => setParamDetailLevel(e.target.value)}
                  >
                    <option value="Minimal">Minimal</option>
                    <option value="Summary">Summary</option>
                    <option value="Full">Full</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Don't Show Parameters For:
                  </label>
                  <textarea
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    rows={3}
                    placeholder="ca_riv_share_eligible&#10;ca_riv_share_electricity_emergency_payment"
                    value={noParamsList}
                    onChange={(e) => setNoParamsList(e.target.value)}
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Stop Variables (optional):
              </label>
              <textarea
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                rows={3}
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
          className="w-full bg-blue-600 text-white py-3 rounded-md font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Generating...' : 'Generate Flowchart'}
        </button>

        {/* Error Display */}
        {error && (
          <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        {/* Graph Stats */}
        {graphData && (
          <div className="mt-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
            ✅ Graph generated: {graphData.nodes.length} nodes, {graphData.edges.length} edges
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6">
        <div className="bg-white rounded-lg shadow-lg h-full p-4">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">
            Dependency Flowchart
          </h2>
          <div ref={networkContainer} className="w-full h-[calc(100%-3rem)]" />
        </div>
      </div>
    </div>
  );
}

export default App;