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

  // Spacing scale - consistent spacing throughout the app
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
    xxl: '48px',
  },

  // Typography scale
  typography: {
    fontFamily: {
      sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      mono: '"Menlo", "Monaco", "Courier New", monospace',
    },
    fontSize: {
      xs: '11px',
      sm: '13px',
      base: '14px',
      md: '16px',
      lg: '18px',
      xl: '20px',
      xxl: '24px',
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.75,
    },
  },

  // Border radius scale
  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    full: '9999px',
  },

  // Shadow scale
  shadows: {
    sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px rgba(0, 0, 0, 0.07)',
    lg: '0 10px 15px rgba(0, 0, 0, 0.1)',
    xl: '0 20px 25px rgba(0, 0, 0, 0.15)',
  },

  // Transitions
  transitions: {
    fast: '150ms ease-in-out',
    normal: '200ms ease-in-out',
    slow: '300ms ease-in-out',
  },

  // Component-specific styles
  components: {
    sidebar: {
      width: '360px',
      padding: '24px',
    },
    input: {
      height: '40px',
      padding: '8px 12px',
      fontSize: '14px',
    },
    button: {
      height: '44px',
      padding: '12px 24px',
      fontSize: '14px',
    },
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