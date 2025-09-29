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
const { colors, spacing, typography, borderRadius, shadows, transitions } = PolicyEngineTheme;

// Icon components
const SearchIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8"></circle>
    <path d="m21 21-4.35-4.35"></path>
  </svg>
);

const ChevronIcon = ({ open }: { open: boolean }) => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    style={{
      transform: open ? 'rotate(180deg)' : 'rotate(0)',
      transition: transitions.normal
    }}
  >
    <polyline points="6 9 12 15 18 9"></polyline>
  </svg>
);

const ClearIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);

const LoadingSpinner = () => (
  <div className="spinner" style={{
    width: '16px',
    height: '16px',
    border: `2px solid ${colors.WHITE}`,
    borderTopColor: 'transparent',
    borderRadius: borderRadius.full
  }}></div>
);

function App() {
  // State
  const [variables, setVariables] = useState<Variable[]>([]);
  const [selectedVariable, setSelectedVariable] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [showSearchResults, setShowSearchResults] = useState<boolean>(false);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [detailsOpen, setDetailsOpen] = useState<boolean>(false);
  const [selectedCountry, setSelectedCountry] = useState<string>('US');
  const [legendExpanded, setLegendExpanded] = useState<boolean>(true);

  // Controls
  const [maxDepth, setMaxDepth] = useState<number>(10);
  const [expandAddsSubtracts, setExpandAddsSubtracts] = useState<boolean>(true);
  const [showParameters, setShowParameters] = useState<boolean>(true);
  const [paramDetailLevel, setParamDetailLevel] = useState<string>('Summary');
  const [stopVariables, setStopVariables] = useState<string[]>([]);
  const [stopVarSearch, setStopVarSearch] = useState<string>('');
  const [showStopVarDropdown, setShowStopVarDropdown] = useState<boolean>(false);
  const [noParamsList, setNoParamsList] = useState<string[]>([]);
  const [noParamsSearch, setNoParamsSearch] = useState<string>('');
  const [showNoParamsDropdown, setShowNoParamsDropdown] = useState<boolean>(false);

  const networkContainer = useRef<HTMLDivElement>(null);
  const networkInstance = useRef<Network | null>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);
  const stopVarContainerRef = useRef<HTMLDivElement>(null);
  const noParamsContainerRef = useRef<HTMLDivElement>(null);

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
      if (stopVarContainerRef.current && !stopVarContainerRef.current.contains(event.target as Node)) {
        setShowStopVarDropdown(false);
      }
      if (noParamsContainerRef.current && !noParamsContainerRef.current.contains(event.target as Node)) {
        setShowNoParamsDropdown(false);
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
        showLabels: true,
        stopVariables: stopVariables,
        noParamsList: noParamsList
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
      physics: { enabled: false },
      nodes: {
        borderWidth: 2,
        borderWidthSelected: 4,
        margin: { top: 10, right: 15, bottom: 10, left: 15 },
        widthConstraint: { maximum: 250 },
        heightConstraint: { minimum: 40 },
        font: {
          size: 14,
          face: typography.fontFamily.sans,
          bold: { face: typography.fontFamily.sans }
        },
        shape: 'box',
        shadow: {
          enabled: true,
          color: 'rgba(0,0,0,0.1)',
          size: 10,
          x: 2,
          y: 2
        },
        chosen: {
          node: function(values: any, id: any, selected: any, hovering: any) {
            if (hovering) {
              values.borderWidth = 3;
              values.shadow = true;
              values.shadowSize = 14;
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
          to: { enabled: true, scaleFactor: 1.2 }
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        zoomView: true,
        dragView: true,
        navigationButtons: false,
        keyboard: { enabled: false }
      }
    };

    networkInstance.current = new Network(
      networkContainer.current,
      { nodes: data.nodes, edges: data.edges },
      options
    );

    setTimeout(() => {
      if (!networkInstance.current) return;

      const positions = networkInstance.current.getPositions();
      if (!positions) return;

      const levels: Map<number, string[]> = new Map();

      for (const nodeId in positions) {
        const y = Math.round(positions[nodeId].y / 10) * 10;
        if (!levels.has(y)) {
          levels.set(y, []);
        }
        levels.get(y)!.push(nodeId);
      }

      const minSpacing = 180;

      levels.forEach((nodesAtLevel) => {
        if (nodesAtLevel.length <= 1) return;

        nodesAtLevel.sort((a, b) => positions[a].x - positions[b].x);

        const totalWidth = (nodesAtLevel.length - 1) * minSpacing;
        const startX = -totalWidth / 2;

        nodesAtLevel.forEach((nodeId, index) => {
          const newX = startX + (index * minSpacing);
          networkInstance.current?.moveNode(nodeId, newX, positions[nodeId].y);
        });
      });

      networkInstance.current.fit();
    }, 100);

    networkInstance.current.on("hoverNode", function () {
      document.body.style.cursor = 'pointer';
    });

    networkInstance.current.on("blurNode", function () {
      document.body.style.cursor = 'default';
    });

    networkInstance.current.on("stabilizationIterationsDone", function () {
      setTimeout(() => {
        if (networkInstance.current) {
          networkInstance.current.fit({
            animation: {
              duration: 1000,
              easingFunction: 'easeInOutQuad'
            }
          });
        }
      }, 100);
    });

    networkInstance.current.stabilize();
  };

  const filteredVariables = searchTerm.length >= 2
    ? variables.filter(v =>
        v.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (v.label || '').toLowerCase().includes(searchTerm.toLowerCase())
      )
    : variables;

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      width: '100vw',
      backgroundColor: colors.BLUE_98,
      overflow: 'hidden',
      fontFamily: typography.fontFamily.sans
    }}>
      {/* Sidebar */}
      <aside style={{
        width: '380px',
        flexShrink: 0,
        backgroundColor: colors.WHITE,
        borderRight: `1px solid ${colors.BLUE_95}`,
        boxShadow: shadows.lg,
        overflowY: 'auto',
        height: '100vh'
      }}>
        <div style={{ padding: spacing.lg }}>
          {/* Header */}
          <header style={{
            padding: spacing.lg,
            background: `linear-gradient(135deg, ${colors.BLUE_PRIMARY} 0%, ${colors.TEAL_ACCENT} 100%)`,
            borderRadius: borderRadius.lg,
            boxShadow: shadows.md,
            marginBottom: spacing.lg
          }}>
            <h1 style={{
              fontSize: typography.fontSize.xl,
              fontWeight: typography.fontWeight.bold,
              color: colors.WHITE,
              margin: 0,
              marginBottom: spacing.xs
            }}>
              PolicyEngine Flowchart
            </h1>
            <p style={{
              fontSize: typography.fontSize.sm,
              color: colors.BLUE_98,
              margin: 0,
              marginBottom: spacing.md,
              opacity: 0.95
            }}>
              Visualize variable dependencies
            </p>

            {/* Country Selector */}
            <select
              value={selectedCountry}
              onChange={(e) => {
                setSelectedCountry(e.target.value);
                setSelectedVariable('');
                setSearchTerm('');
                setError('');
                setGraphData(null);
              }}
              style={{
                width: '100%',
                padding: spacing.sm,
                fontSize: typography.fontSize.sm,
                borderRadius: borderRadius.md,
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                color: colors.DARKEST_BLUE,
                border: `1px solid ${colors.BLUE_95}`,
                outline: 'none',
                cursor: 'pointer',
                fontWeight: typography.fontWeight.medium,
                transition: transitions.normal
              }}
            >
              <option value="US">🇺🇸 United States</option>
              <option value="UK">🇬🇧 United Kingdom</option>
            </select>
          </header>

          {/* Search Section */}
          <section style={{ marginBottom: spacing.lg, position: 'relative' }} ref={searchContainerRef}>
            <label style={{
              display: 'block',
              fontSize: typography.fontSize.sm,
              fontWeight: typography.fontWeight.semibold,
              marginBottom: spacing.sm,
              color: colors.DARKEST_BLUE
            }}>
              Search Variables
            </label>
            <div style={{ position: 'relative' }}>
              <div style={{
                position: 'absolute',
                left: spacing.md,
                top: '50%',
                transform: 'translateY(-50%)',
                color: colors.DARK_GRAY,
                pointerEvents: 'none'
              }}>
                <SearchIcon />
              </div>
              <input
                type="text"
                placeholder="Type variable name..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  searchVariables(e.target.value);
                }}
                onFocus={() => {
                  if (searchTerm.length >= 2) setShowSearchResults(true);
                }}
                style={{
                  width: '100%',
                  height: '44px',
                  paddingLeft: '44px',
                  paddingRight: spacing.md,
                  fontSize: typography.fontSize.base,
                  border: `2px solid ${colors.BLUE_95}`,
                  borderRadius: borderRadius.md,
                  backgroundColor: colors.WHITE,
                  outline: 'none',
                  transition: transitions.normal,
                  boxShadow: shadows.sm
                }}
                onFocusCapture={(e) => {
                  e.currentTarget.style.borderColor = colors.TEAL_ACCENT;
                  e.currentTarget.style.boxShadow = `0 0 0 3px ${colors.TEAL_LIGHT}`;
                }}
                onBlurCapture={(e) => {
                  e.currentTarget.style.borderColor = colors.BLUE_95;
                  e.currentTarget.style.boxShadow = shadows.sm;
                }}
              />

              {/* Dropdown */}
              {showSearchResults && searchTerm.length >= 2 && (
                <div style={{
                  position: 'absolute',
                  zIndex: 10,
                  width: '100%',
                  marginTop: spacing.sm,
                  backgroundColor: colors.WHITE,
                  borderRadius: borderRadius.md,
                  boxShadow: shadows.xl,
                  maxHeight: '320px',
                  overflowY: 'auto',
                  border: `1px solid ${colors.BLUE_95}`
                }}>
                {filteredVariables.slice(0, 10).map(v => (
                  <div
                    key={v.name}
                    onClick={() => selectVariable(v.name)}
                    style={{
                      padding: `${spacing.md} ${spacing.md}`,
                      cursor: 'pointer',
                      transition: transitions.fast,
                      borderBottom: `1px solid ${colors.BLUE_98}`,
                      fontSize: typography.fontSize.sm
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = colors.TEAL_LIGHT;
                      e.currentTarget.style.paddingLeft = spacing.lg;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                      e.currentTarget.style.paddingLeft = spacing.md;
                    }}
                  >
                    <div style={{
                      fontFamily: typography.fontFamily.mono,
                      fontWeight: typography.fontWeight.semibold,
                      color: colors.DARKEST_BLUE,
                      fontSize: typography.fontSize.sm
                    }}>
                      {v.name}
                    </div>
                  </div>
                ))}
                {filteredVariables.length === 0 && (
                  <div style={{
                    padding: spacing.md,
                    fontSize: typography.fontSize.sm,
                    color: colors.DARK_GRAY
                  }}>
                    No variables found matching "{searchTerm}"
                  </div>
                )}
                </div>
              )}
            </div>
          </section>

          {/* Selected Variable */}
          {selectedVariable && (
            <div style={{
              marginBottom: spacing.lg,
              padding: spacing.md,
              borderRadius: borderRadius.md,
              backgroundColor: colors.TEAL_LIGHT,
              border: `2px solid ${colors.TEAL_ACCENT}`
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ flex: 1 }}>
                  <div style={{
                    fontSize: typography.fontSize.xs,
                    fontWeight: typography.fontWeight.medium,
                    marginBottom: spacing.xs,
                    color: colors.DARK_GRAY
                  }}>
                    Selected Variable ({selectedCountry})
                  </div>
                  <div style={{
                    fontFamily: typography.fontFamily.mono,
                    fontSize: typography.fontSize.sm,
                    fontWeight: typography.fontWeight.bold,
                    color: colors.TEAL_PRESSED
                  }}>
                    {selectedVariable}
                  </div>
                </div>
                <button
                  onClick={() => {
                    setSelectedVariable('');
                    setSearchTerm('');
                    loadVariables();
                  }}
                  style={{
                    padding: spacing.sm,
                    borderRadius: borderRadius.md,
                    color: colors.TEAL_PRESSED,
                    backgroundColor: colors.WHITE,
                    border: `1px solid ${colors.TEAL_ACCENT}`,
                    cursor: 'pointer',
                    transition: transitions.normal,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = colors.TEAL_ACCENT;
                    e.currentTarget.style.color = colors.WHITE;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = colors.WHITE;
                    e.currentTarget.style.color = colors.TEAL_PRESSED;
                  }}
                >
                  <ClearIcon />
                </button>
              </div>
            </div>
          )}

          {/* Advanced Options */}
          <div style={{
            marginBottom: spacing.lg,
            borderRadius: borderRadius.md,
            overflow: 'visible',
            backgroundColor: colors.BLUE_98,
            border: `1px solid ${colors.BLUE_95}`
          }}>
            <button
              onClick={() => setDetailsOpen(!detailsOpen)}
              style={{
                width: '100%',
                padding: spacing.md,
                fontSize: typography.fontSize.sm,
                fontWeight: typography.fontWeight.semibold,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: colors.DARKEST_BLUE,
                backgroundColor: detailsOpen ? colors.BLUE_95 : 'transparent',
                border: 'none',
                cursor: 'pointer',
                transition: transitions.normal
              }}
            >
              <span>⚙️ Advanced Options</span>
              <ChevronIcon open={detailsOpen} />
            </button>

            {detailsOpen && (
              <div style={{ padding: spacing.md }}>
                {/* Max Depth */}
                <div style={{ marginBottom: spacing.md }}>
                  <label style={{
                    display: 'block',
                    fontSize: typography.fontSize.xs,
                    fontWeight: typography.fontWeight.medium,
                    marginBottom: spacing.sm,
                    color: colors.DARKEST_BLUE
                  }}>
                    Max Depth: <span style={{ fontWeight: typography.fontWeight.bold, fontSize: typography.fontSize.sm }}>{maxDepth}</span>
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="20"
                    value={maxDepth}
                    onChange={(e) => setMaxDepth(Number(e.target.value))}
                    style={{
                      width: '100%',
                      accentColor: colors.TEAL_ACCENT,
                      cursor: 'pointer'
                    }}
                  />
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: typography.fontSize.xs,
                    marginTop: spacing.xs,
                    color: colors.DARK_GRAY
                  }}>
                    <span>1</span>
                    <span>20</span>
                  </div>
                </div>

                {/* Checkboxes */}
                <div style={{ marginBottom: spacing.md }}>
                  {[
                    { label: 'Expand Adds/Subtracts', checked: expandAddsSubtracts, onChange: setExpandAddsSubtracts },
                    { label: 'Show Parameters', checked: showParameters, onChange: setShowParameters }
                  ].map((item, idx) => (
                    <label key={idx} style={{
                      display: 'flex',
                      alignItems: 'center',
                      fontSize: typography.fontSize.xs,
                      cursor: 'pointer',
                      padding: spacing.sm,
                      borderRadius: borderRadius.sm,
                      transition: transitions.fast,
                      marginBottom: spacing.xs
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = colors.WHITE}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    >
                      <input
                        type="checkbox"
                        checked={item.checked}
                        onChange={(e) => item.onChange(e.target.checked)}
                        style={{
                          marginRight: spacing.sm,
                          accentColor: colors.TEAL_ACCENT,
                          cursor: 'pointer'
                        }}
                      />
                      <span style={{ color: colors.DARKEST_BLUE }}>{item.label}</span>
                    </label>
                  ))}
                </div>

                {/* Parameter Options */}
                {showParameters && (
                  <>
                    <div style={{ marginBottom: spacing.md }}>
                      <label style={{
                        display: 'block',
                        fontSize: typography.fontSize.xs,
                        fontWeight: typography.fontWeight.medium,
                        marginBottom: spacing.xs,
                        color: colors.DARKEST_BLUE
                      }}>
                        Parameter Detail Level
                      </label>
                      <select
                        value={paramDetailLevel}
                        onChange={(e) => setParamDetailLevel(e.target.value)}
                        style={{
                          width: '100%',
                          padding: spacing.sm,
                          fontSize: typography.fontSize.xs,
                          borderRadius: borderRadius.md,
                          border: `1px solid ${colors.BLUE_95}`,
                          backgroundColor: colors.WHITE,
                          cursor: 'pointer'
                        }}
                      >
                        <option value="Minimal">Minimal</option>
                        <option value="Summary">Summary</option>
                        <option value="Full">Full</option>
                      </select>
                    </div>

                    <div style={{ marginBottom: spacing.md }}>
                      <label style={{
                        display: 'block',
                        fontSize: typography.fontSize.xs,
                        fontWeight: typography.fontWeight.medium,
                        marginBottom: spacing.xs,
                        color: colors.DARKEST_BLUE
                      }}>
                        Don't Show Parameters For:
                      </label>

                      {/* Selected no-params variables as chips */}
                      {noParamsList.length > 0 && (
                        <div style={{
                          display: 'flex',
                          flexWrap: 'wrap',
                          gap: spacing.xs,
                          marginBottom: spacing.sm,
                          padding: spacing.sm,
                          backgroundColor: colors.BLUE_98,
                          borderRadius: borderRadius.sm,
                          border: `1px solid ${colors.BLUE_95}`
                        }}>
                          {noParamsList.map((variable, idx) => (
                            <div
                              key={idx}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: spacing.xs,
                                padding: `${spacing.xs} ${spacing.sm}`,
                                backgroundColor: colors.TEAL_ACCENT,
                                color: colors.WHITE,
                                borderRadius: borderRadius.sm,
                                fontSize: typography.fontSize.xs,
                                fontFamily: typography.fontFamily.mono
                              }}
                            >
                              <span>{variable}</span>
                              <button
                                onClick={() => {
                                  setNoParamsList(noParamsList.filter((_, i) => i !== idx));
                                }}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  padding: '2px',
                                  backgroundColor: 'transparent',
                                  color: colors.WHITE,
                                  border: 'none',
                                  cursor: 'pointer',
                                  borderRadius: borderRadius.sm,
                                  transition: transitions.fast
                                }}
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.backgroundColor = 'transparent';
                                }}
                              >
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <line x1="18" y1="6" x2="6" y2="18"></line>
                                  <line x1="6" y1="6" x2="18" y2="18"></line>
                                </svg>
                              </button>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Search input for no-params variables */}
                      <div style={{ position: 'relative' }} ref={noParamsContainerRef}>
                        <input
                          type="text"
                          placeholder="Search to add variables..."
                          value={noParamsSearch}
                          onChange={(e) => {
                            setNoParamsSearch(e.target.value);
                            if (e.target.value.length >= 2) {
                              setShowNoParamsDropdown(true);
                            } else {
                              setShowNoParamsDropdown(false);
                            }
                          }}
                          onFocus={() => {
                            if (noParamsSearch.length >= 2) setShowNoParamsDropdown(true);
                          }}
                          style={{
                            width: '100%',
                            padding: spacing.sm,
                            fontSize: typography.fontSize.xs,
                            borderRadius: borderRadius.md,
                            border: `1px solid ${colors.BLUE_95}`,
                            backgroundColor: colors.WHITE,
                            outline: 'none',
                            transition: transitions.normal,
                            fontFamily: typography.fontFamily.mono
                          }}
                          onFocusCapture={(e) => {
                            e.currentTarget.style.borderColor = colors.TEAL_ACCENT;
                            e.currentTarget.style.boxShadow = `0 0 0 2px ${colors.TEAL_LIGHT}`;
                          }}
                          onBlurCapture={(e) => {
                            e.currentTarget.style.borderColor = colors.BLUE_95;
                            e.currentTarget.style.boxShadow = 'none';
                          }}
                        />

                        {/* Dropdown for no-params variables */}
                        {showNoParamsDropdown && noParamsSearch.length >= 2 && (
                          <div style={{
                            position: 'absolute',
                            zIndex: 100,
                            width: '100%',
                            marginTop: spacing.xs,
                            backgroundColor: colors.WHITE,
                            borderRadius: borderRadius.md,
                            boxShadow: shadows.xl,
                            maxHeight: '200px',
                            overflowY: 'auto',
                            border: `1px solid ${colors.BLUE_95}`
                          }}>
                            {variables
                              .filter(v =>
                                (v.name.toLowerCase().includes(noParamsSearch.toLowerCase()) ||
                                (v.label || '').toLowerCase().includes(noParamsSearch.toLowerCase())) &&
                                !noParamsList.includes(v.name)
                              )
                              .slice(0, 8)
                              .map(v => (
                                <div
                                  key={v.name}
                                  onClick={() => {
                                    if (!noParamsList.includes(v.name)) {
                                      setNoParamsList([...noParamsList, v.name]);
                                      setNoParamsSearch('');
                                      setShowNoParamsDropdown(false);
                                    }
                                  }}
                                  style={{
                                    padding: spacing.sm,
                                    cursor: 'pointer',
                                    transition: transitions.fast,
                                    borderBottom: `1px solid ${colors.BLUE_98}`,
                                    fontSize: typography.fontSize.xs,
                                    fontFamily: typography.fontFamily.mono
                                  }}
                                  onMouseEnter={(e) => {
                                    e.currentTarget.style.backgroundColor = colors.TEAL_LIGHT;
                                  }}
                                  onMouseLeave={(e) => {
                                    e.currentTarget.style.backgroundColor = 'transparent';
                                  }}
                                >
                                  {v.name}
                                </div>
                              ))}
                            {variables.filter(v =>
                              (v.name.toLowerCase().includes(noParamsSearch.toLowerCase()) ||
                              (v.label || '').toLowerCase().includes(noParamsSearch.toLowerCase())) &&
                              !noParamsList.includes(v.name)
                            ).length === 0 && (
                              <div style={{
                                padding: spacing.sm,
                                fontSize: typography.fontSize.xs,
                                color: colors.DARK_GRAY
                              }}>
                                No variables found
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}

                {/* Stop Variables */}
                <div>
                  <label style={{
                    display: 'block',
                    fontSize: typography.fontSize.xs,
                    fontWeight: typography.fontWeight.medium,
                    marginBottom: spacing.xs,
                    color: colors.DARKEST_BLUE
                  }}>
                    Stop Variables:
                  </label>

                  {/* Selected stop variables as chips */}
                  {stopVariables.length > 0 && (
                    <div style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: spacing.xs,
                      marginBottom: spacing.sm,
                      padding: spacing.sm,
                      backgroundColor: colors.BLUE_98,
                      borderRadius: borderRadius.sm,
                      border: `1px solid ${colors.BLUE_95}`
                    }}>
                      {stopVariables.map((variable, idx) => (
                        <div
                          key={idx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: spacing.xs,
                            padding: `${spacing.xs} ${spacing.sm}`,
                            backgroundColor: colors.BLUE_PRIMARY,
                            color: colors.WHITE,
                            borderRadius: borderRadius.sm,
                            fontSize: typography.fontSize.xs,
                            fontFamily: typography.fontFamily.mono
                          }}
                        >
                          <span>{variable}</span>
                          <button
                            onClick={() => {
                              setStopVariables(stopVariables.filter((_, i) => i !== idx));
                            }}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              padding: '2px',
                              backgroundColor: 'transparent',
                              color: colors.WHITE,
                              border: 'none',
                              cursor: 'pointer',
                              borderRadius: borderRadius.sm,
                              transition: transitions.fast
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.backgroundColor = 'transparent';
                            }}
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <line x1="18" y1="6" x2="6" y2="18"></line>
                              <line x1="6" y1="6" x2="18" y2="18"></line>
                            </svg>
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Search input for stop variables */}
                  <div style={{ position: 'relative' }} ref={stopVarContainerRef}>
                    <input
                      type="text"
                      placeholder="Search to add stop variables..."
                      value={stopVarSearch}
                      onChange={(e) => {
                        setStopVarSearch(e.target.value);
                        if (e.target.value.length >= 2) {
                          setShowStopVarDropdown(true);
                        } else {
                          setShowStopVarDropdown(false);
                        }
                      }}
                      onFocus={() => {
                        if (stopVarSearch.length >= 2) setShowStopVarDropdown(true);
                      }}
                      style={{
                        width: '100%',
                        padding: spacing.sm,
                        fontSize: typography.fontSize.xs,
                        borderRadius: borderRadius.md,
                        border: `1px solid ${colors.BLUE_95}`,
                        backgroundColor: colors.WHITE,
                        outline: 'none',
                        transition: transitions.normal,
                        fontFamily: typography.fontFamily.mono
                      }}
                      onFocusCapture={(e) => {
                        e.currentTarget.style.borderColor = colors.TEAL_ACCENT;
                        e.currentTarget.style.boxShadow = `0 0 0 2px ${colors.TEAL_LIGHT}`;
                      }}
                      onBlurCapture={(e) => {
                        e.currentTarget.style.borderColor = colors.BLUE_95;
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    />

                    {/* Dropdown for stop variables */}
                    {showStopVarDropdown && stopVarSearch.length >= 2 && (
                      <div style={{
                        position: 'absolute',
                        zIndex: 100,
                        width: '100%',
                        marginTop: spacing.xs,
                        backgroundColor: colors.WHITE,
                        borderRadius: borderRadius.md,
                        boxShadow: shadows.xl,
                        maxHeight: '200px',
                        overflowY: 'auto',
                        border: `1px solid ${colors.BLUE_95}`
                      }}>
                        {variables
                          .filter(v =>
                            (v.name.toLowerCase().includes(stopVarSearch.toLowerCase()) ||
                            (v.label || '').toLowerCase().includes(stopVarSearch.toLowerCase())) &&
                            !stopVariables.includes(v.name)
                          )
                          .slice(0, 8)
                          .map(v => (
                            <div
                              key={v.name}
                              onClick={() => {
                                if (!stopVariables.includes(v.name)) {
                                  setStopVariables([...stopVariables, v.name]);
                                  setStopVarSearch('');
                                  setShowStopVarDropdown(false);
                                }
                              }}
                              style={{
                                padding: spacing.sm,
                                cursor: 'pointer',
                                transition: transitions.fast,
                                borderBottom: `1px solid ${colors.BLUE_98}`,
                                fontSize: typography.fontSize.xs,
                                fontFamily: typography.fontFamily.mono
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.backgroundColor = colors.TEAL_LIGHT;
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.backgroundColor = 'transparent';
                              }}
                            >
                              {v.name}
                            </div>
                          ))}
                        {variables.filter(v =>
                          (v.name.toLowerCase().includes(stopVarSearch.toLowerCase()) ||
                          (v.label || '').toLowerCase().includes(stopVarSearch.toLowerCase())) &&
                          !stopVariables.includes(v.name)
                        ).length === 0 && (
                          <div style={{
                            padding: spacing.sm,
                            fontSize: typography.fontSize.xs,
                            color: colors.DARK_GRAY
                          }}>
                            No variables found
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Generate Button */}
          <button
            onClick={generateFlowchart}
            disabled={loading || !selectedVariable}
            style={{
              width: '100%',
              height: '48px',
              padding: spacing.md,
              borderRadius: borderRadius.md,
              fontSize: typography.fontSize.base,
              fontWeight: typography.fontWeight.semibold,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: spacing.sm,
              backgroundColor: loading || !selectedVariable ? colors.MEDIUM_LIGHT_GRAY : colors.BLUE_PRIMARY,
              color: colors.WHITE,
              border: 'none',
              boxShadow: loading || !selectedVariable ? 'none' : shadows.md,
              cursor: loading || !selectedVariable ? 'not-allowed' : 'pointer',
              transition: transitions.normal,
              marginBottom: spacing.md
            }}
            onMouseEnter={(e) => {
              if (!loading && selectedVariable) {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = shadows.lg;
              }
            }}
            onMouseLeave={(e) => {
              if (!loading && selectedVariable) {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = shadows.md;
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
            <div style={{
              marginBottom: spacing.md,
              padding: spacing.md,
              borderRadius: borderRadius.md,
              fontSize: typography.fontSize.xs,
              display: 'flex',
              alignItems: 'flex-start',
              gap: spacing.sm,
              backgroundColor: '#FEF2F2',
              border: `1px solid ${colors.DARK_RED}`,
              color: colors.DARK_RED
            }}>
              <span>⚠️</span>
              <div>
                <strong>Error:</strong> {error}
              </div>
            </div>
          )}

          {/* Legend */}
          {graphData && (
            <div style={{
              padding: spacing.md,
              borderRadius: borderRadius.md,
              backgroundColor: colors.WHITE,
              border: `1px solid ${colors.BLUE_95}`,
              boxShadow: shadows.sm
            }}>
              <h3
                onClick={() => setLegendExpanded(!legendExpanded)}
                style={{
                  fontSize: typography.fontSize.sm,
                  fontWeight: typography.fontWeight.semibold,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: spacing.xs,
                  color: colors.DARKEST_BLUE,
                  userSelect: 'none',
                  margin: 0
                }}
              >
                Legend
                <ChevronIcon open={legendExpanded} />
              </h3>

              {legendExpanded && (
                <div style={{ marginTop: spacing.md }}>
                  {/* Nodes */}
                  <div style={{ marginBottom: spacing.md }}>
                    <p style={{
                      fontSize: typography.fontSize.xs,
                      fontWeight: typography.fontWeight.semibold,
                      marginBottom: spacing.sm,
                      color: colors.DARKEST_BLUE
                    }}>
                      Nodes
                    </p>
                    <div style={{ paddingLeft: spacing.md }}>
                      {[
                        { color: colors.TEAL_ACCENT, label: 'Root' },
                        { color: colors.BLUE_PRIMARY, label: 'Dependency' },
                        { color: colors.DARK_RED, label: 'Stop' },
                        { color: '#8B4B9B', label: 'Defined For' }
                      ].map((item, idx) => (
                        <div key={idx} style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: spacing.md,
                          marginBottom: spacing.sm
                        }}>
                          <div style={{
                            width: '14px',
                            height: '14px',
                            borderRadius: borderRadius.full,
                            backgroundColor: item.color,
                            flexShrink: 0
                          }}></div>
                          <span style={{
                            fontSize: typography.fontSize.xs,
                            color: colors.DARK_GRAY
                          }}>
                            {item.label}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Edges */}
                  <div>
                    <p style={{
                      fontSize: typography.fontSize.xs,
                      fontWeight: typography.fontWeight.semibold,
                      marginBottom: spacing.sm,
                      color: colors.DARKEST_BLUE
                    }}>
                      Edges
                    </p>
                    <div style={{ paddingLeft: spacing.md }}>
                      {[
                        { color: colors.GREEN, label: 'Addition', symbol: '+' },
                        { color: colors.DARK_RED, label: 'Subtraction', symbol: '-' },
                        { color: colors.GRAY, label: 'Reference', symbol: '→' }
                      ].map((item, idx) => (
                        <div key={idx} style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: spacing.sm,
                          marginBottom: spacing.sm
                        }}>
                          <span style={{
                            fontSize: typography.fontSize.sm,
                            fontWeight: typography.fontWeight.bold,
                            color: item.color,
                            minWidth: '24px'
                          }}>
                            {item.symbol}
                          </span>
                          <span style={{
                            fontSize: typography.fontSize.xs,
                            color: colors.DARK_GRAY
                          }}>
                            {item.label}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* Main Graph Area */}
      <main style={{
        flex: 1,
        padding: spacing.lg,
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden'
      }}>
        <div
          ref={networkContainer}
          style={{
            width: '100%',
            height: '100%',
            backgroundColor: colors.WHITE,
            boxShadow: shadows.lg,
            border: `1px solid ${colors.BLUE_95}`,
            borderRadius: borderRadius.lg,
            flex: 1
          }}
        ></div>
      </main>
    </div>
  );
}

export default App;