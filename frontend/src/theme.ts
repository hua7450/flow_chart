// PolicyEngine Brand Colors - Official Style Guide v2.6
export const PolicyEngineTheme = {
  colors: {
    // Primary colors
    BLACK: "#000000",
    WHITE: "#FFFFFF",
    
    // Blue palette
    BLUE_PRIMARY: "#2C6496",
    BLUE: "#2C6496",
    BLUE_PRESSED: "#17354F",
    DARK_BLUE_HOVER: "#1d3e5e",
    DARKEST_BLUE: "#0C1A27",
    BLUE_LIGHT: "#D8E6F3",
    BLUE_95: "#D8E6F3",
    BLUE_98: "#F7FAFD",
    
    // Teal palette
    TEAL_ACCENT: "#39C6C0",
    TEAL_LIGHT: "#F7FDFC",
    TEAL_PRESSED: "#227773",
    
    // Gray palette
    GRAY: "#808080",
    DARK_GRAY: "#616161",
    LIGHT_GRAY: "#F2F2F2",
    MEDIUM_DARK_GRAY: "#D2D2D2",
    MEDIUM_LIGHT_GRAY: "#BDBDBD",
    
    // Semantic colors
    GREEN: "#29d40f",
    DARK_RED: "#b50d0d",
  },
  
  // Graph-specific colors
  graph: {
    // Node colors
    targetNode: {
      background: "#39C6C0", // TEAL_ACCENT for target
      border: "#227773", // TEAL_PRESSED
      highlight: {
        background: "#39C6C0",
        border: "#227773"
      }
    },
    stopNode: {
      background: "#F7FAFD", // BLUE_98
      border: "#b50d0d", // DARK_RED
      highlight: {
        background: "#ffebeb",
        border: "#b50d0d"
      }
    },
    normalNode: {
      background: "#D8E6F3", // BLUE_LIGHT
      border: "#2C6496", // BLUE_PRIMARY
      highlight: {
        background: "#F7FAFD", // BLUE_98
        border: "#2C6496"
      }
    },
    
    // Edge colors
    addsEdge: {
      color: "#29d40f", // GREEN
      highlight: "#29d40f"
    },
    subtractsEdge: {
      color: "#b50d0d", // DARK_RED
      highlight: "#b50d0d"
    },
    normalEdge: {
      color: "#808080", // GRAY
      highlight: "#616161" // DARK_GRAY
    }
  }
};

export default PolicyEngineTheme;