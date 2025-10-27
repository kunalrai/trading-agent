/**
 * Tailwind CSS Configuration for SolSignals
 */

// SolSignals Tailwind configuration
const solSignalsConfig = {
    darkMode: "class",
    theme: {
        extend: {
            colors: {
                "primary": "#13a4ec",
                "background-light": "#f6f7f8",
                "background-dark": "#101c22",
                'dark-bg': '#0f1419',
                'dark-card': '#1a1f2e',
                'dark-border': '#2d3748',
                'crypto-green': '#10b981',
                'crypto-red': '#ef4444',
                'crypto-blue': '#3b82f6',
                'crypto-purple': '#8b5cf6',
                'text-muted': '#6b7280',
            },
            fontFamily: {
                "display": ["Space Grotesk", "sans-serif"],
                'system': ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif']
            },
            borderRadius: {
                "DEFAULT": "0.25rem",
                "lg": "0.5rem",
                "xl": "0.75rem",
                "full": "9999px"
            },
            animation: {
                'pulse-slow': 'pulse 3s infinite',
                'bounce-slow': 'bounce 2s infinite',
                'fade-in': 'fadeIn 0.5s ease-in',
                'slide-up': 'slideUp 0.3s ease-out',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' }
                },
                slideUp: {
                    '0%': { transform: 'translateY(100%)' },
                    '100%': { transform: 'translateY(0)' }
                }
            },
            boxShadow: {
                'glow-blue': '0 0 20px rgba(59, 130, 246, 0.5)',
                'glow-green': '0 0 20px rgba(16, 185, 129, 0.5)',
                'glow-purple': '0 0 20px rgba(139, 92, 246, 0.5)',
            }
        }
    }
};

// Apply configuration if Tailwind is available
if (typeof tailwind !== 'undefined') {
    tailwind.config = solSignalsConfig;
}