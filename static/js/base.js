/**
 * Base JavaScript for SolSignals Application
 * Common utilities and functions used across all pages
 */

// SolSignals Application Namespace
window.SolSignals = {
    // Configuration
    config: {
        apiBaseUrl: '/api',
        refreshInterval: 30000, // 30 seconds
        chartUpdateInterval: 5000, // 5 seconds
    },
    
    // Utility functions
    utils: {
        /**
         * Format price with currency symbol
         */
        formatPrice: function(price, currency = '$') {
            if (!price || isNaN(price)) return currency + '0.00';
            return currency + parseFloat(price).toFixed(2);
        },
        
        /**
         * Format percentage with proper sign and color
         */
        formatPercentage: function(percentage) {
            if (!percentage || isNaN(percentage)) return '0.00%';
            const value = parseFloat(percentage).toFixed(2);
            const sign = value >= 0 ? '+' : '';
            return sign + value + '%';
        },
        
        /**
         * Get color class for price change
         */
        getPriceChangeColor: function(value) {
            if (value > 0) return 'text-green-400';
            if (value < 0) return 'text-red-400';
            return 'text-white/80';
        },
        
        /**
         * Format timestamp to readable format
         */
        formatTimestamp: function(timestamp) {
            const date = new Date(timestamp);
            return date.toLocaleString();
        },
        
        /**
         * Debounce function for performance
         */
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        /**
         * Show notification
         */
        showNotification: function(message, type = 'info') {
            // Create notification element
            const notification = document.createElement('div');
            notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 ${
                type === 'success' ? 'bg-green-500' :
                type === 'error' ? 'bg-red-500' :
                type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'
            } text-white`;
            notification.textContent = message;
            
            document.body.appendChild(notification);
            
            // Auto remove after 5 seconds
            setTimeout(() => {
                notification.style.opacity = '0';
                setTimeout(() => {
                    document.body.removeChild(notification);
                }, 300);
            }, 5000);
        }
    },
    
    // API functions
    api: {
        /**
         * Generic API call function
         */
        call: async function(endpoint, options = {}) {
            try {
                const response = await fetch(SolSignals.config.apiBaseUrl + endpoint, {
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    ...options
                });
                
                if (!response.ok) {
                    throw new Error(`API call failed: ${response.status}`);
                }
                
                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                SolSignals.utils.showNotification('API call failed', 'error');
                throw error;
            }
        },
        
        /**
         * Get breakout scanner data
         */
        getBreakoutData: function() {
            return this.call('/breakout-data');
        },
        
        /**
         * Get futures prices data
         */
        getFuturesPrices: function() {
            return this.call('/futures-prices');
        },
        
        /**
         * Get symbol details
         */
        getSymbolDetails: function(symbol) {
            return this.call(`/symbol/${symbol}/details`);
        },
        
        /**
         * Health check
         */
        healthCheck: function() {
            return this.call('/health');
        },
        
        /**
         * Get latest trading data (backward compatibility)
         */
        getLatestData: function() {
            return this.getBreakoutData();
        },
        
        /**
         * Get chart data (placeholder for future implementation)
         */
        getChartData: function(hours = 24) {
            // TODO: Implement chart data endpoint
            return Promise.resolve({ data: [], timestamp: Date.now() });
        }
    },
    
    // Navigation functions
    navigation: {
        /**
         * Update active navigation state
         */
        updateActiveNav: function() {
            const currentPath = window.location.pathname;
            const navLinks = document.querySelectorAll('.nav-link');
            
            navLinks.forEach(link => {
                const href = link.getAttribute('href');
                if (href === currentPath || (currentPath === '/' && href === '/')) {
                    link.classList.add('text-primary');
                    link.classList.remove('text-white/80');
                } else {
                    link.classList.remove('text-primary');
                    link.classList.add('text-white/80');
                }
            });
        },
        
        /**
         * Navigate to coin detail page
         */
        goToCoinDetail: function(symbol) {
            window.location.href = `/coin/${symbol}`;
        }
    },
    
    // Real-time data updates
    realtime: {
        intervals: {},
        
        /**
         * Start real-time updates for a component
         */
        start: function(componentName, updateFunction, interval = null) {
            interval = interval || SolSignals.config.refreshInterval;
            
            // Clear existing interval if any
            if (this.intervals[componentName]) {
                clearInterval(this.intervals[componentName]);
            }
            
            // Start new interval
            this.intervals[componentName] = setInterval(updateFunction, interval);
            
            // Run immediately
            updateFunction();
        },
        
        /**
         * Stop real-time updates for a component
         */
        stop: function(componentName) {
            if (this.intervals[componentName]) {
                clearInterval(this.intervals[componentName]);
                delete this.intervals[componentName];
            }
        },
        
        /**
         * Stop all real-time updates
         */
        stopAll: function() {
            Object.keys(this.intervals).forEach(componentName => {
                this.stop(componentName);
            });
        }
    }
};

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Update navigation active state
    SolSignals.navigation.updateActiveNav();
    
    // Add click handlers for coin links
    document.querySelectorAll('[data-coin-symbol]').forEach(element => {
        element.addEventListener('click', function(e) {
            e.preventDefault();
            const symbol = this.getAttribute('data-coin-symbol');
            SolSignals.navigation.goToCoinDetail(symbol);
        });
    });
    
    // Initialize tooltips
    document.querySelectorAll('[title]').forEach(element => {
        element.addEventListener('mouseenter', function() {
            // Simple tooltip implementation
            const tooltip = document.createElement('div');
            tooltip.className = 'absolute z-50 px-2 py-1 bg-black text-white text-xs rounded shadow-lg';
            tooltip.textContent = this.title;
            tooltip.style.top = (this.offsetTop - 30) + 'px';
            tooltip.style.left = this.offsetLeft + 'px';
            document.body.appendChild(tooltip);
            
            this._tooltip = tooltip;
        });
        
        element.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                document.body.removeChild(this._tooltip);
                this._tooltip = null;
            }
        });
    });
});

// Clean up intervals when page unloads
window.addEventListener('beforeunload', function() {
    SolSignals.realtime.stopAll();
});

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    SolSignals.utils.showNotification('An error occurred', 'error');
});

// Export for module environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SolSignals;
}