/**
 * SolSignals Dashboard JavaScript
 * Handles real-time data updates, chart management, and user interactions
 */

// Global variables
let priceChart, gapChart, volumeChart, liveChart;
let liveDataInterval = null;
let isLiveUpdating = true;
let liveDataPoints = [];
let liveEmaPoints = [];
let liveSupportResistance = null;

// Register annotation and zoom plugins
if (typeof Chart !== 'undefined') {
    if (window.chartjsPluginAnnotation) {
        Chart.register(window.chartjsPluginAnnotation.default || window.chartjsPluginAnnotation);
    }
    if (window.chartjsPluginZoom) {
        Chart.register(window.chartjsPluginZoom.default || window.chartjsPluginZoom);
    }
}

// Chart configuration constants
const CHART_COLORS = {
    price: '#10b981',
    priceBackground: 'rgba(16, 185, 129, 0.1)',
    ema: '#3b82f6',
    emaBackground: 'rgba(59, 130, 246, 0.1)',
    gap: '#8b5cf6',
    gapBackground: 'rgba(139, 92, 246, 0.2)',
    volume: '#3b82f6',
    volumeBackground: 'rgba(59, 130, 246, 0.6)',
    support: '#10b981',
    supportBackground: 'rgba(16, 185, 129, 0.2)',
    resistance: '#ef4444',
    resistanceBackground: 'rgba(239, 68, 68, 0.2)',
    text: '#f9fafb',
    muted: '#6b7280',
    grid: 'rgba(107, 114, 128, 0.2)'
};

// Initialize charts with dark theme
function initCharts() {
    // Price Chart
    const priceCtx = document.getElementById('priceChart').getContext('2d');
    priceChart = new Chart(priceCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Price',
                data: [],
                borderColor: CHART_COLORS.price,
                backgroundColor: CHART_COLORS.priceBackground,
                tension: 0.4,
                fill: true,
                borderWidth: 2
            }, {
                label: 'EMA',
                data: [],
                borderColor: CHART_COLORS.ema,
                backgroundColor: CHART_COLORS.emaBackground,
                tension: 0.4,
                fill: false,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    labels: { 
                        color: CHART_COLORS.text,
                        font: { size: 12 }
                    }
                },
                annotation: {
                    annotations: {}
                },
                zoom: {
                    pan: {
                        enabled: true,
                        mode: 'xy',
                        modifierKey: 'ctrl'
                    },
                    zoom: {
                        wheel: {
                            enabled: true,
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'xy',
                        onZoomComplete: function(chart) {
                            // Optional: Add custom logic after zoom
                            console.log('Zoom completed on price chart');
                        }
                    },
                    limits: {
                        y: {min: 'original', max: 'original'},
                        x: {min: 'original', max: 'original'}
                    }
                }
            },
            scales: {
                x: { 
                    ticks: { 
                        color: CHART_COLORS.muted, 
                        font: { size: 11 } 
                    },
                    grid: { color: CHART_COLORS.grid }
                },
                y: { 
                    ticks: { 
                        color: CHART_COLORS.muted, 
                        font: { size: 11 } 
                    },
                    grid: { color: CHART_COLORS.grid }
                }
            }
        }
    });

    // Gap Chart
    const gapCtx = document.getElementById('gapChart').getContext('2d');
    gapChart = new Chart(gapCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Price-EMA Gap',
                data: [],
                borderColor: function(context) {
                    if (context.parsed) {
                        return context.parsed.y >= 0 ? CHART_COLORS.price : CHART_COLORS.gap;
                    }
                    return CHART_COLORS.gap;
                },
                backgroundColor: function(context) {
                    if (context.parsed) {
                        return context.parsed.y >= 0 ? CHART_COLORS.priceBackground : CHART_COLORS.gapBackground;
                    }
                    return CHART_COLORS.gapBackground;
                },
                tension: 0.4,
                fill: true,
                borderWidth: 2,
                pointBackgroundColor: function(context) {
                    if (context.parsed) {
                        return context.parsed.y >= 0 ? CHART_COLORS.price : CHART_COLORS.gap;
                    }
                    return CHART_COLORS.gap;
                }
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    labels: { 
                        color: CHART_COLORS.text,
                        font: { size: 12 }
                    }
                },
                zoom: {
                    pan: {
                        enabled: true,
                        mode: 'xy'
                    },
                    zoom: {
                        wheel: {
                            enabled: true,
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'xy'
                    }
                }
            },
            scales: {
                x: { 
                    ticks: { 
                        color: CHART_COLORS.muted, 
                        font: { size: 11 } 
                    },
                    grid: { color: CHART_COLORS.grid }
                },
                y: { 
                    ticks: { 
                        color: CHART_COLORS.muted, 
                        font: { size: 11 },
                        callback: function(value) {
                            return (value >= 0 ? '+$' : '-$') + Math.abs(value).toFixed(4);
                        }
                    },
                    grid: { 
                        color: CHART_COLORS.grid,
                        drawBorder: false
                    }
                }
            }
        }
    });

    // Volume Chart
    const volumeCtx = document.getElementById('volumeChart').getContext('2d');
    volumeChart = new Chart(volumeCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Volume',
                data: [],
                backgroundColor: CHART_COLORS.volumeBackground,
                borderColor: CHART_COLORS.volume,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    labels: { 
                        color: CHART_COLORS.text,
                        font: { size: 12 }
                    }
                },
                zoom: {
                    pan: {
                        enabled: true,
                        mode: 'x'
                    },
                    zoom: {
                        wheel: {
                            enabled: true,
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x'
                    }
                }
            },
            scales: {
                x: { 
                    ticks: { 
                        color: CHART_COLORS.muted, 
                        font: { size: 11 } 
                    },
                    grid: { color: CHART_COLORS.grid }
                },
                y: { 
                    ticks: { 
                        color: CHART_COLORS.muted, 
                        font: { size: 11 },
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    },
                    grid: { color: CHART_COLORS.grid }
                }
            }
        }
    });

    // Live Price Chart
    const liveCtx = document.getElementById('liveChart').getContext('2d');
    liveChart = new Chart(liveCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Live Price',
                data: [],
                borderColor: CHART_COLORS.price,
                backgroundColor: CHART_COLORS.priceBackground,
                tension: 0.1,
                fill: false,
                borderWidth: 3,
                pointRadius: 2,
                pointHoverRadius: 5
            }, {
                label: 'Live EMA',
                data: [],
                borderColor: CHART_COLORS.ema,
                backgroundColor: CHART_COLORS.emaBackground,
                tension: 0.1,
                fill: false,
                borderWidth: 2,
                pointRadius: 1,
                pointHoverRadius: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 750
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    labels: { 
                        color: CHART_COLORS.text,
                        font: { size: 12 }
                    }
                },
                annotation: {
                    annotations: {}
                },
                zoom: {
                    pan: {
                        enabled: true,
                        mode: 'xy',
                        modifierKey: 'ctrl'
                    },
                    zoom: {
                        wheel: {
                            enabled: true,
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'xy'
                    }
                }
            },
            scales: {
                x: { 
                    ticks: { 
                        color: CHART_COLORS.muted, 
                        font: { size: 11 },
                        maxTicksLimit: 20
                    },
                    grid: { color: CHART_COLORS.grid }
                },
                y: { 
                    ticks: { 
                        color: CHART_COLORS.muted, 
                        font: { size: 11 },
                        callback: function(value) {
                            return '$' + value.toFixed(4);
                        }
                    },
                    grid: { color: CHART_COLORS.grid }
                }
            }
        }
    });
}

// Live Data Functions
async function startLiveUpdates() {
    if (isLiveUpdating) return;
    
    isLiveUpdating = true;
    const toggleBtn = document.getElementById('toggleLive');
    if (toggleBtn) {
        toggleBtn.textContent = 'Stop Live Updates';
        toggleBtn.classList.remove('bg-green-600', 'hover:bg-green-700');
        toggleBtn.classList.add('bg-red-600', 'hover:bg-red-700');
    }
    
    await updateLiveData(); // Initial load
    liveDataInterval = setInterval(updateLiveData, 5000); // Update every 5 seconds
}

function stopLiveUpdates() {
    if (!isLiveUpdating) return;
    
    isLiveUpdating = false;
    if (liveDataInterval) {
        clearInterval(liveDataInterval);
        liveDataInterval = null;
    }
    
    const toggleBtn = document.getElementById('toggleLive');
    if (toggleBtn) {
        toggleBtn.textContent = 'Start Live Updates';
        toggleBtn.classList.remove('bg-red-600', 'hover:bg-red-700');
        toggleBtn.classList.add('bg-green-600', 'hover:bg-green-700');
    }
}

async function updateLiveData() {
    try {
        // Fetch latest price data
        const response = await fetch('/api/latest-data');
        if (!response.ok) throw new Error('Failed to fetch live data');
        
        const data = await response.json();
        const currentTime = new Date().toLocaleTimeString();
        
        // Add new data point
        liveDataPoints.push({
            time: currentTime,
            price: data.price
        });
        
        if (data.ema) {
            liveEmaPoints.push({
                time: currentTime,
                ema: data.ema
            });
        }
        
        // Keep only last 100 points for performance
        if (liveDataPoints.length > 100) {
            liveDataPoints.shift();
            liveEmaPoints.shift();
        }
        
        // Update chart data
        liveChart.data.labels = liveDataPoints.map(point => point.time);
        liveChart.data.datasets[0].data = liveDataPoints.map(point => point.price);
        liveChart.data.datasets[1].data = liveEmaPoints.map(point => point.ema);
        
        // Update support/resistance if changed
        if (data.support_resistance && 
            JSON.stringify(data.support_resistance) !== JSON.stringify(liveSupportResistance)) {
            liveSupportResistance = data.support_resistance;
            updateLiveSupportResistance();
        }
        
        liveChart.update('none'); // No animation for smoother updates
        
    } catch (error) {
        console.error('Error updating live data:', error);
        // Don't stop updates on single error, just log it
    }
}

function updateLiveSupportResistance() {
    if (!liveChart || !liveSupportResistance) return;
    
    const annotations = {};
    
    // Process support levels (top 3 strongest)
    const supportLevels = liveSupportResistance.support || [];
    supportLevels.slice(0, 3).forEach((level, index) => {
        annotations[`support_${index}`] = {
            type: 'line',
            yMin: level.price,
            yMax: level.price,
            borderColor: CHART_COLORS.support,
            borderWidth: 2,
            borderDash: [5, 5],
            label: {
                content: `S${index + 1}: $${level.price.toFixed(4)}`,
                enabled: true,
                position: 'start',
                backgroundColor: CHART_COLORS.support,
                color: '#ffffff',
                font: { size: 10 }
            }
        };
    });
    
    // Process resistance levels (top 3 strongest)
    const resistanceLevels = liveSupportResistance.resistance || [];
    resistanceLevels.slice(0, 3).forEach((level, index) => {
        annotations[`resistance_${index}`] = {
            type: 'line',
            yMin: level.price,
            yMax: level.price,
            borderColor: CHART_COLORS.resistance,
            borderWidth: 2,
            borderDash: [5, 5],
            label: {
                content: `R${index + 1}: $${level.price.toFixed(4)}`,
                enabled: true,
                position: 'end',
                backgroundColor: CHART_COLORS.resistance,
                color: '#ffffff',
                font: { size: 10 }
            }
        };
    });
    
    liveChart.options.plugins.annotation.annotations = annotations;
    liveChart.update();
}

function clearLiveData() {
    liveDataPoints = [];
    liveEmaPoints = [];
    
    if (liveChart) {
        liveChart.data.labels = [];
        liveChart.data.datasets[0].data = [];
        liveChart.data.datasets[1].data = [];
        liveChart.options.plugins.annotation.annotations = {};
        liveChart.update();
    }
}

function toggleLiveUpdates() {
    if (isLiveUpdating) {
        stopLiveUpdates();
    } else {
        startLiveUpdates();
    }
}

// Update real-time data
function updateData() {
    fetch('/api/data')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Update metrics with animation
            animateValue('current-price', `$${data.price.toFixed(4)}`);
            animateValue('ema-value', `$${data.ema.toFixed(4)}`);
            
            // Format gap with proper sign and color
            const gapElement = document.getElementById('price-gap');
            if (gapElement) {
                const gapValue = data.gap >= 0 ? `+$${data.gap.toFixed(4)}` : `-$${Math.abs(data.gap).toFixed(4)}`;
                const gapColor = data.gap >= 0 ? 'text-crypto-green' : 'text-crypto-red';
                
                if (gapElement.textContent !== gapValue) {
                    gapElement.innerHTML = `<span class="${gapColor}">${gapValue}</span>`;
                    gapElement.style.transform = 'scale(1.05)';
                    gapElement.style.transition = 'transform 0.2s ease';
                    
                    setTimeout(() => {
                        gapElement.style.transform = 'scale(1)';
                    }, 200);
                }
            }
            
            // Update status
            const statusElement = document.getElementById('status-text');
            if (statusElement) {
                statusElement.textContent = data.status;
            }

            // Update signal status with visual feedback
            updateSignalStatus(data);
        })
        .catch(error => {
            console.error('Error updating data:', error);
            showNotification('Error updating data', 'error');
        });
}

// Update signal status with visual effects
function updateSignalStatus(data) {
    const signalStatus = document.getElementById('signal-status');
    const signalCard = document.getElementById('signal-card');
    const signalStrength = document.getElementById('signal-strength');
    const signalReason = document.getElementById('signal-reason');
    
    if (!signalStatus || !signalCard) return;
    
    // Remove all existing signal classes
    signalCard.classList.remove('status-active', 'pulse-green', 'status-waiting', 'pulse-red', 'pulse-blue');
    
    if (data.signal_type && data.signal_type !== 'HOLD') {
        // Update signal display
        let signalHTML = '';
        let cardClass = '';
        
        switch(data.signal_type) {
            case 'STRONG_BUY':
                signalHTML = '<span class="text-green-400">🚀 STRONG BUY</span>';
                cardClass = 'pulse-green';
                break;
            case 'BUY':
                signalHTML = '<span class="text-crypto-green">📈 BUY</span>';
                cardClass = 'pulse-green';
                break;
            case 'STRONG_SELL':
                signalHTML = '<span class="text-red-400">🔻 STRONG SELL</span>';
                cardClass = 'pulse-red';
                break;
            case 'SELL':
                signalHTML = '<span class="text-crypto-red">📉 SELL</span>';
                cardClass = 'pulse-red';
                break;
            default:
                signalHTML = '<span class="text-text-muted">⏸️ HOLD</span>';
                cardClass = 'status-waiting';
        }
        
        signalStatus.innerHTML = signalHTML;
        signalCard.classList.add('status-active', cardClass);
        
        // Update signal strength
        if (signalStrength && data.signal_strength) {
            signalStrength.textContent = `Confidence: ${Math.round(data.signal_strength * 100)}%`;
        }
        
        // Update signal reason
        if (signalReason && data.signal_reason) {
            signalReason.textContent = data.signal_reason;
        }
        
    } else {
        signalStatus.innerHTML = '<span class="text-text-muted">⏸️ HOLD</span>';
        signalCard.classList.add('status-waiting');
        
        if (signalStrength) {
            signalStrength.textContent = 'Waiting for signal';
        }
    }
}

// Animate value changes
function animateValue(elementId, newValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const oldValue = element.textContent;
    if (oldValue !== newValue) {
        element.style.transform = 'scale(1.05)';
        element.style.transition = 'transform 0.2s ease';
        element.textContent = newValue;
        
        // Add color coding for gap values
        if (elementId === 'price-gap') {
            const gapValue = parseFloat(newValue.replace(/[^-\d.]/g, ''));
            if (gapValue > 0) {
                element.style.color = '#10b981'; // Green for positive
            } else if (gapValue < 0) {
                element.style.color = '#ef4444'; // Red for negative
            } else {
                element.style.color = '#ffffff'; // White for zero
            }
        }
        
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 200);
    }
}

// Update support and resistance levels on the price chart
function updateSupportResistance(supportResistanceData) {
    if (!priceChart || !supportResistanceData) return;
    
    // Clear existing annotations
    if (priceChart.options.plugins.annotation) {
        priceChart.options.plugins.annotation.annotations = {};
    }
    
    const annotations = {};
    
    // Get current price for distance calculations
    const currentPrice = priceChart.data.datasets[0].data.slice(-1)[0] || 0;
    
    // Filter and limit support levels to show only the most relevant ones (max 3)
    if (supportResistanceData.support_levels && supportResistanceData.support_levels.length > 0) {
        const relevantSupports = supportResistanceData.support_levels
            .filter(level => level < currentPrice) // Only levels below current price
            .sort((a, b) => b - a) // Sort by distance from current price (closest first)
            .slice(0, 3); // Take only top 3
        
        relevantSupports.forEach((level, index) => {
            const distance = Math.abs(currentPrice - level);
            const distancePercent = ((distance / currentPrice) * 100).toFixed(2);
            const strength = relevantSupports.length - index; // Strength based on proximity
            
            annotations[`support_${index}`] = {
                type: 'line',
                yMin: level,
                yMax: level,
                borderColor: CHART_COLORS.support,
                borderWidth: index === 0 ? 2.5 : 2, // Thicker for closest level
                borderDash: [5, 5],
                label: {
                    content: `S${index + 1}: $${level.toFixed(4)} (${distancePercent}% away)`,
                    enabled: true,
                    position: 'start',
                    backgroundColor: CHART_COLORS.supportBackground,
                    color: CHART_COLORS.support,
                    font: {
                        size: 10
                    }
                },
                // Add tooltip information
                id: `support_${index}`,
                onClick: () => {
                    showNotification(`Support Level ${index + 1}: $${level.toFixed(4)} - Distance: ${distancePercent}% - Strength: ${strength}/3`, 'info');
                }
            };
        });
    }
    
    // Filter and limit resistance levels to show only the most relevant ones (max 3)
    if (supportResistanceData.resistance_levels && supportResistanceData.resistance_levels.length > 0) {
        const relevantResistances = supportResistanceData.resistance_levels
            .filter(level => level > currentPrice) // Only levels above current price
            .sort((a, b) => a - b) // Sort by distance from current price (closest first)
            .slice(0, 3); // Take only top 3
        
        relevantResistances.forEach((level, index) => {
            const distance = Math.abs(level - currentPrice);
            const distancePercent = ((distance / currentPrice) * 100).toFixed(2);
            const strength = relevantResistances.length - index; // Strength based on proximity
            
            annotations[`resistance_${index}`] = {
                type: 'line',
                yMin: level,
                yMax: level,
                borderColor: CHART_COLORS.resistance,
                borderWidth: index === 0 ? 2.5 : 2, // Thicker for closest level
                borderDash: [5, 5],
                label: {
                    content: `R${index + 1}: $${level.toFixed(4)} (${distancePercent}% away)`,
                    enabled: true,
                    position: 'start',
                    backgroundColor: CHART_COLORS.resistanceBackground,
                    color: CHART_COLORS.resistance,
                    font: {
                        size: 10
                    }
                },
                // Add tooltip information
                id: `resistance_${index}`,
                onClick: () => {
                    showNotification(`Resistance Level ${index + 1}: $${level.toFixed(4)} - Distance: ${distancePercent}% - Strength: ${strength}/3`, 'info');
                }
            };
        });
    }
    
    // Highlight current support and resistance with thicker lines and enhanced tooltips
    if (supportResistanceData.current_support) {
        const supportDistance = Math.abs(currentPrice - supportResistanceData.current_support);
        const supportDistancePercent = ((supportDistance / currentPrice) * 100).toFixed(2);
        
        annotations['current_support'] = {
            type: 'line',
            yMin: supportResistanceData.current_support,
            yMax: supportResistanceData.current_support,
            borderColor: CHART_COLORS.support,
            borderWidth: 4, // Thicker for current levels
            borderDash: [8, 4], // Different dash pattern
            label: {
                content: `🟢 ACTIVE SUPPORT: $${supportResistanceData.current_support.toFixed(4)} (${supportDistancePercent}% below)`,
                enabled: true,
                position: 'end',
                backgroundColor: CHART_COLORS.support,
                color: '#ffffff',
                font: {
                    size: 12,
                    weight: 'bold'
                }
            },
            onClick: () => {
                showNotification(`Current Support: $${supportResistanceData.current_support.toFixed(4)} - This is the nearest support level below current price (${supportDistancePercent}% away)`, 'success');
            }
        };
    }
    
    if (supportResistanceData.current_resistance) {
        const resistanceDistance = Math.abs(supportResistanceData.current_resistance - currentPrice);
        const resistanceDistancePercent = ((resistanceDistance / currentPrice) * 100).toFixed(2);
        
        annotations['current_resistance'] = {
            type: 'line',
            yMin: supportResistanceData.current_resistance,
            yMax: supportResistanceData.current_resistance,
            borderColor: CHART_COLORS.resistance,
            borderWidth: 4, // Thicker for current levels
            borderDash: [8, 4], // Different dash pattern
            label: {
                content: `🔴 ACTIVE RESISTANCE: $${supportResistanceData.current_resistance.toFixed(4)} (${resistanceDistancePercent}% above)`,
                enabled: true,
                position: 'end',
                backgroundColor: CHART_COLORS.resistance,
                color: '#ffffff',
                font: {
                    size: 12,
                    weight: 'bold'
                }
            },
            onClick: () => {
                showNotification(`Current Resistance: $${supportResistanceData.current_resistance.toFixed(4)} - This is the nearest resistance level above current price (${resistanceDistancePercent}% away)`, 'error');
            }
        };
    }
    
    // Update chart with annotations
    priceChart.options.plugins.annotation.annotations = annotations;
    priceChart.update('none');
}

// Update candlestick chart with support and resistance
function updateCandlestickSupportResistance(supportResistanceData) {
    console.log('Candlestick support/resistance function deprecated - using live chart instead');
}

// Legacy function placeholders (for HTML compatibility)
function updateCandlestickData(hours = 4) {
    console.log('Candlestick chart has been replaced with live chart');
    showNotification('Live chart is now active', 'info');
}

// Live chart zoom controls
function zoomInLive() {
    if (liveChart) {
        liveChart.zoom(1.1);
        showNotification('Live chart zoomed in', 'info');
    }
}

function zoomOutLive() {
    if (liveChart) {
        liveChart.zoom(0.9);
        showNotification('Live chart zoomed out', 'info');
    }
}

function resetZoomLive() {
    if (liveChart) {
        liveChart.resetZoom();
        showNotification('Live chart zoom reset', 'info');
    }
}

// Update chart data from database
function updateChartData(hours = 24) {
    // Update button states
    document.querySelectorAll('button[onclick*="updateChartData"]').forEach(btn => {
        btn.className = 'glass-button px-3 py-1 rounded text-sm text-gray-400';
    });
    
    if (event && event.target) {
        event.target.className = 'glass-button px-3 py-1 rounded text-sm text-crypto-blue';
    }
    
    // Show loading state
    showLoading(['priceChart', 'gapChart', 'volumeChart']);
    
    fetch(`/api/chart-data?hours=${hours}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Limit charts to last N points to keep X-axis readable
            const MAX_POINTS = 10; // change this value to show more/less

            const labels = Array.isArray(data.labels) ? data.labels.slice(-MAX_POINTS) : [];
            const prices = Array.isArray(data.prices) ? data.prices.slice(-MAX_POINTS) : [];
            const ema_values = Array.isArray(data.ema_values) ? data.ema_values.slice(-MAX_POINTS) : [];
            const gaps = Array.isArray(data.gaps) ? data.gaps.slice(-MAX_POINTS) : [];
            const volumes = Array.isArray(data.volumes) ? data.volumes.slice(-MAX_POINTS) : [];

            // Update price chart
            if (priceChart) {
                priceChart.data.labels = labels;
                if (priceChart.data.datasets[0]) priceChart.data.datasets[0].data = prices;
                if (priceChart.data.datasets[1]) priceChart.data.datasets[1].data = ema_values;
                priceChart.update('none'); // No animation for better performance
            }

            // Update gap chart
            if (gapChart) {
                gapChart.data.labels = labels;
                if (gapChart.data.datasets[0]) gapChart.data.datasets[0].data = gaps;
                gapChart.update('none');
            }

            // Update volume chart
            if (volumeChart) {
                volumeChart.data.labels = labels;
                if (volumeChart.data.datasets[0]) volumeChart.data.datasets[0].data = volumes;
                volumeChart.update('none');
            }

            // Update support and resistance levels
            if (data.support_resistance) {
                updateSupportResistance(data.support_resistance);
            }

            hideLoading(['priceChart', 'gapChart', 'volumeChart']);
        })
        .catch(error => {
            console.error('Error updating chart data:', error);
            showNotification('Error updating charts', 'error');
            hideLoading(['priceChart', 'gapChart', 'volumeChart']);
        });
}

// Refresh trading signals
function refreshSignals() {
    const refreshBtn = event ? event.target : null;
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Loading...';
    }
    
    fetch('/api/signals?limit=10')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(signals => {
            const tbody = document.getElementById('signals-table');
            if (!tbody) return;
            
            tbody.innerHTML = '';
            
            signals.forEach((signal, index) => {
                const row = tbody.insertRow();
                const time = new Date(signal.timestamp);
                row.className = 'border-b border-dark-border fade-in';
                row.style.animationDelay = `${index * 0.1}s`;
                
                row.innerHTML = `
                    <td class="py-3 text-sm text-gray-300">${time.toLocaleTimeString()}</td>
                    <td class="py-3 text-sm text-crypto-green">$${signal.price.toFixed(4)}</td>
                    <td class="py-3 text-sm text-crypto-blue">$${signal.ema_value.toFixed(4)}</td>
                    <td class="py-3 text-sm text-crypto-purple">$${signal.gap.toFixed(4)}</td>
                    <td class="py-3 text-sm">
                        <span class="px-2 py-1 bg-crypto-green rounded-full text-xs font-medium">
                            ${signal.signal_type}
                        </span>
                    </td>
                `;
            });
            
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-refresh mr-2"></i>Refresh';
            }
        })
        .catch(error => {
            console.error('Error refreshing signals:', error);
            showNotification('Error refreshing signals', 'error');
            
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-refresh mr-2"></i>Refresh';
            }
        });
}

// Update database stats
function updateStats() {
    fetch('/api/stats')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(stats => {
            animateValue('price-records', stats.price_records || '0');
            animateValue('signal-records', stats.signal_records || '0');
            
            // Convert KB to MB and display
            const dbSizeMB = stats.database_size_kb ? (stats.database_size_kb / 1024).toFixed(2) : '0.00';
            animateValue('db-size', dbSizeMB);
        })
        .catch(error => {
            console.error('Error updating stats:', error);
        });
}

// Show loading state
function showLoading(elementIds) {
    if (!Array.isArray(elementIds)) {
        console.warn('showLoading: elementIds must be an array');
        return;
    }
    
    elementIds.forEach(id => {
        try {
            const element = document.getElementById(id);
            if (element) {
                const container = element.closest('.chart-container, .chart-container-main');
                if (container) {
                    container.classList.add('loading');
                } else {
                    console.warn(`No chart container found for element: ${id}`);
                }
            } else {
                console.warn(`Element not found: ${id}`);
            }
        } catch (error) {
            console.error(`Error in showLoading for element ${id}:`, error);
        }
    });
}

// Hide loading state
function hideLoading(elementIds) {
    if (!Array.isArray(elementIds)) {
        console.warn('hideLoading: elementIds must be an array');
        return;
    }
    
    elementIds.forEach(id => {
        try {
            const element = document.getElementById(id);
            if (element) {
                const container = element.closest('.chart-container, .chart-container-main');
                if (container) {
                    container.classList.remove('loading');
                } else {
                    console.warn(`No chart container found for element: ${id}`);
                }
            } else {
                console.warn(`Element not found: ${id}`);
            }
        } catch (error) {
            console.error(`Error in hideLoading for element ${id}:`, error);
        }
    });
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    let bgColor = 'bg-blue-600';
    if (type === 'error') bgColor = 'bg-red-600';
    if (type === 'success') bgColor = 'bg-green-600';
    
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${bgColor} text-white`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Error handling for charts
function handleChartError(error, chartName) {
    console.error(`Error in ${chartName}:`, error);
    showNotification(`Chart error: ${chartName}`, 'error');
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Check if all required chart elements exist
        const requiredElements = ['priceChart', 'gapChart', 'volumeChart', 'liveChart'];
        const missingElements = requiredElements.filter(id => !document.getElementById(id));
        
        if (missingElements.length > 0) {
            console.warn('Missing chart elements:', missingElements);
            showNotification('Some chart elements are missing', 'error');
            return;
        }
        
        initCharts();
        
        // Wait a bit before calling updateChartData to ensure charts are initialized
        setTimeout(() => {
            updateChartData();
            updateCandlestickData(4); // Load 4 hours of candlestick data by default
        }, 100);
        
        refreshSignals();
        refreshAlerts();
        updateStats();
        
        // Set up auto-refresh with error handling
        setInterval(() => {
            try {
                updateData();
            } catch (error) {
                console.error('Error in updateData interval:', error);
            }
        }, 5000);
        
        setInterval(() => {
            try {
                updateChartData();
            } catch (error) {
                console.error('Error in updateChartData interval:', error);
            }
        }, 60000);
        
        setInterval(() => {
            try {
                refreshSignals();
            } catch (error) {
                console.error('Error in refreshSignals interval:', error);
            }
        }, 30000);
        
        setInterval(() => {
            try {
                refreshAlerts();
            } catch (error) {
                console.error('Error in refreshAlerts interval:', error);
            }
        }, 60000);
        
        setInterval(() => {
            try {
                updateStats();
            } catch (error) {
                console.error('Error in updateStats interval:', error);
            }
        }, 120000);
        
        // Add event listener for adding symbols with Enter key
        const newSymbolInput = document.getElementById('new-symbol');
        if (newSymbolInput) {
            newSymbolInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    addSymbolToWatchlist();
                }
            });
        }
        
        console.log('SolSignals Dashboard initialized successfully');
        
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showNotification('Error initializing dashboard', 'error');
    }
});

// Handle page visibility change (pause updates when tab is not active)
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('Page hidden, pausing updates');
    } else {
        console.log('Page visible, resuming updates');
        updateData();
        updateChartData();
    }
});

// Manual database cleanup
function manualCleanup() {
    if (!confirm('Are you sure you want to clean up old database records? This action cannot be undone.')) {
        return;
    }
    
    const cleanupBtn = event.target;
    const originalText = cleanupBtn.innerHTML;
    
    // Show loading state
    cleanupBtn.disabled = true;
    cleanupBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Cleaning...';
    
    fetch('/api/cleanup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            retention_days: 7  // Keep last 7 days
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(
                `Cleanup completed: ${data.deleted_records} records deleted. ` +
                `Database size reduced from ${data.size_before_mb}MB to ${data.size_after_mb}MB.`,
                'success'
            );
            // Refresh stats
            updateStats();
        } else {
            showNotification(`Cleanup failed: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Error during cleanup:', error);
        showNotification('Error during cleanup', 'error');
    })
    .finally(() => {
        // Restore button
        cleanupBtn.disabled = false;
        cleanupBtn.innerHTML = originalText;
    });
}

// Alert Management Functions
function createAlert() {
    const condition = document.getElementById('alert-condition').value;
    const threshold = document.getElementById('alert-threshold').value;
    const notification = document.getElementById('alert-notification').value;
    
    if (!condition || !threshold || !notification) {
        showNotification('Please fill in all alert fields', 'error');
        return;
    }
    
    const alertData = {
        condition_type: condition,
        threshold_value: parseFloat(threshold),
        notification_method: notification
    };
    
    fetch('/api/alerts', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(alertData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Alert created successfully', 'success');
            // Clear form
            document.getElementById('alert-condition').value = '';
            document.getElementById('alert-threshold').value = '';
            document.getElementById('alert-notification').value = '';
            // Refresh alerts table
            refreshAlerts();
        } else {
            showNotification(data.error || 'Failed to create alert', 'error');
        }
    })
    .catch(error => {
        console.error('Error creating alert:', error);
        showNotification('Error creating alert', 'error');
    });
}

function refreshAlerts() {
    const refreshBtn = event ? event.target : null;
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Loading...';
    }
    
    fetch('/api/alerts')
        .then(response => response.json())
        .then(alerts => {
            const tbody = document.getElementById('alerts-table');
            if (!tbody) return;
            
            tbody.innerHTML = '';
            
            if (alerts.length === 0) {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td colspan="5" class="py-6 text-center text-text-muted">
                        No active alerts configured
                    </td>
                `;
                return;
            }
            
            alerts.forEach((alert, index) => {
                const row = tbody.insertRow();
                row.className = 'border-b border-dark-border fade-in';
                row.style.animationDelay = `${index * 0.1}s`;
                
                const lastTriggered = alert.last_triggered ? 
                    new Date(alert.last_triggered).toLocaleString() : 'Never';
                
                row.innerHTML = `
                    <td class="py-3 text-sm text-gray-300">${alert.condition_type}</td>
                    <td class="py-3 text-sm text-crypto-blue">${alert.threshold_value}</td>
                    <td class="py-3 text-sm text-gray-400">${alert.notification_method}</td>
                    <td class="py-3 text-sm">
                        <span class="px-2 py-1 bg-crypto-green rounded-full text-xs font-medium">
                            ${alert.status}
                        </span>
                    </td>
                    <td class="py-3 text-sm">
                        <button onclick="toggleAlert(${alert.id})" 
                                class="text-crypto-blue hover:text-white text-sm mr-2">
                            Toggle
                        </button>
                        <span class="text-xs text-text-muted">Last: ${lastTriggered}</span>
                    </td>
                `;
            });
            
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-refresh mr-2"></i>Refresh';
            }
        })
        .catch(error => {
            console.error('Error refreshing alerts:', error);
            showNotification('Error refreshing alerts', 'error');
            
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-refresh mr-2"></i>Refresh';
            }
        });
}

function toggleAlert(alertId) {
    fetch(`/api/alerts/${alertId}/toggle`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Alert status updated', 'success');
            refreshAlerts();
        } else {
            showNotification(data.error || 'Failed to update alert', 'error');
        }
    })
    .catch(error => {
        console.error('Error toggling alert:', error);
        showNotification('Error updating alert', 'error');
    });
}

// Zoom control functions
function zoomIn() {
    if (priceChart) {
        priceChart.zoom(1.1); // Zoom in by 10%
    }
    if (volumeChart) {
        volumeChart.zoom(1.1);
    }
    if (gapChart) {
        gapChart.zoom(1.1);
    }
    showNotification('Zoomed in', 'info');
}

function zoomOut() {
    if (priceChart) {
        priceChart.zoom(0.9); // Zoom out by 10%
    }
    if (volumeChart) {
        volumeChart.zoom(0.9);
    }
    if (gapChart) {
        gapChart.zoom(0.9);
    }
    showNotification('Zoomed out', 'info');
}

function resetZoom() {
    if (priceChart) {
        priceChart.resetZoom();
    }
    if (volumeChart) {
        volumeChart.resetZoom();
    }
    if (gapChart) {
        gapChart.resetZoom();
    }
    showNotification('Zoom reset', 'info');
}

// Export functions for global access
window.updateChartData = updateChartData;
window.toggleLiveUpdates = toggleLiveUpdates;
window.clearLiveData = clearLiveData;
window.refreshSignals = refreshSignals;
window.createAlert = createAlert;
window.refreshAlerts = refreshAlerts;
window.toggleAlert = toggleAlert;
window.manualCleanup = manualCleanup;
window.zoomIn = zoomIn;
window.zoomOut = zoomOut;
window.resetZoom = resetZoom;
window.zoomInLive = zoomInLive;
window.zoomOutLive = zoomOutLive;
window.resetZoomLive = resetZoomLive;

// Breakout Scanner Variables
let scannerInterval = null;
let scannerRunning = false;
let watchlistSymbols = ['SOL/USDT', 'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT'];
let breakoutSignals = [];
let scannerStats = {
    totalBreakouts: 0,
    bullishSignals: 0,
    bearishSignals: 0,
    accuracyRate: 0
};

// Tab Management
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
        btn.classList.remove('bg-crypto-blue', 'text-white');
        btn.classList.add('text-gray-400');
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    // Activate selected tab
    const activeBtn = document.getElementById(`tab-${tabName}`);
    const activeContent = document.getElementById(`content-${tabName}`);
    
    if (activeBtn && activeContent) {
        activeBtn.classList.add('active', 'bg-crypto-blue', 'text-white');
        activeBtn.classList.remove('text-gray-400');
        activeContent.classList.remove('hidden');
    }
    
    // Initialize scanner UI if switching to scanner tab
    if (tabName === 'scanner') {
        updateScannerStats();
        initializeSortControls();
    }
}

// Breakout Scanner Functions
async function toggleBreakoutScanner() {
    if (scannerRunning) {
        stopBreakoutScanner();
    } else {
        startBreakoutScanner();
    }
}

function startBreakoutScanner() {
    const intervalMs = parseInt(document.getElementById('scanner-interval').value) * 1000;
    
    scannerRunning = true;
    updateScannerStatus();
    
    // Start scanning immediately
    scanForBreakouts();
    
    // Set up interval scanning
    scannerInterval = setInterval(scanForBreakouts, intervalMs);
    
    showNotification('Breakout scanner started', 'success');
}

function stopBreakoutScanner() {
    scannerRunning = false;
    
    if (scannerInterval) {
        clearInterval(scannerInterval);
        scannerInterval = null;
    }
    
    updateScannerStatus();
    showNotification('Breakout scanner stopped', 'info');
}

async function scanForBreakouts() {
    try {
        const volumeThreshold = parseFloat(document.getElementById('volume-threshold').value);
        const priceThreshold = parseFloat(document.getElementById('price-threshold').value);
        
        const symbolsParam = watchlistSymbols.join(',');
        const response = await fetch(`/api/breakout-scanner?symbols=${symbolsParam}&volume_threshold=${volumeThreshold}&price_threshold=${priceThreshold}`);
        
        if (!response.ok) throw new Error('Failed to fetch breakout data');
        
        const data = await response.json();
        
        if (data.success && data.signals) {
            // Process new signals
            for (const signal of data.signals) {
                addBreakoutSignal(signal);
            }
            
            updateScannerStats();
            updateLastScanTime();
        }
        
    } catch (error) {
        console.error('Error scanning for breakouts:', error);
        showNotification('Error scanning for breakouts', 'error');
    }
}

function addBreakoutSignal(signal) {
    // Check if signal already exists (avoid duplicates)
    const existingIndex = breakoutSignals.findIndex(s => 
        s.symbol === signal.symbol && 
        Math.abs(new Date(s.timestamp) - new Date(signal.timestamp)) < 60000 // Within 1 minute
    );
    
    if (existingIndex === -1) {
        // Add new signal
        breakoutSignals.unshift(signal); // Add to beginning
        
        // Limit to last 50 signals
        if (breakoutSignals.length > 50) {
            breakoutSignals = breakoutSignals.slice(0, 50);
        }
        
        // Update statistics
        scannerStats.totalBreakouts++;
        if (signal.signal_type.includes('BULLISH')) {
            scannerStats.bullishSignals++;
        } else if (signal.signal_type.includes('BEARISH')) {
            scannerStats.bearishSignals++;
        }
        
        updateBreakoutTable();
        
        // Show notification for strong signals
        if (signal.signal_strength >= 50) {
            showNotification(`🚨 Strong ${signal.signal_type} detected in ${signal.symbol}`, 'info');
        }
    }
}

function updateBreakoutTable() {
    const tbody = document.getElementById('breakout-table-body');
    
    if (breakoutSignals.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-12">
                    <div class="flex flex-col items-center space-y-4">
                        <i class="fas fa-radar-chart text-4xl text-gray-600"></i>
                        <div class="text-gray-400">
                            <div class="text-lg font-medium">No Breakouts Detected</div>
                            <div class="text-sm">Scanner is monitoring symbols for breakout signals</div>
                        </div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    // Sort signals by strength (highest first)
    const sortedSignals = [...breakoutSignals].sort((a, b) => b.signal_strength - a.signal_strength);
    
    tbody.innerHTML = sortedSignals.map((signal, index) => {
        const rank = index + 1;
        const changeClass = signal.price_change_pct >= 0 ? 'change-positive' : 'change-negative';
        const breakoutBadge = getBreakoutBadge(signal.signal_type);
        const strengthBar = getStrengthBar(signal.signal_strength);
        const volumeClass = getVolumeClass(signal.volume_ratio);
        const timeDisplay = formatTimeAgo(new Date(signal.timestamp));
        
        return `
            <tr class="hover:bg-gray-800 transition-colors">
                <td class="rank-cell">${rank}</td>
                <td class="py-4 px-6">
                    <div class="crypto-name">
                        <div class="crypto-symbol">${signal.symbol.split('/')[0]}</div>
                        <div class="crypto-full-name">${getCryptoFullName(signal.symbol.split('/')[0])}</div>
                    </div>
                </td>
                <td class="price-cell">$${signal.price.toFixed(4)}</td>
                <td class="${changeClass}">
                    ${signal.price_change_pct >= 0 ? '+' : ''}${signal.price_change_pct.toFixed(2)}%
                </td>
                <td class="volume-ratio ${volumeClass}">
                    ${signal.volume_ratio.toFixed(1)}x
                </td>
                <td class="py-4 px-6">
                    <div class="space-y-1">
                        <div class="text-sm font-medium text-white">${signal.signal_strength.toFixed(0)}%</div>
                        ${strengthBar}
                    </div>
                </td>
                <td class="py-4 px-6">
                    ${breakoutBadge}
                </td>
                <td class="time-display">${timeDisplay}</td>
            </tr>
        `;
    }).join('');
}

function getBreakoutBadge(signalType) {
    let badgeClass = 'breakout-badge ';
    let icon = '';
    let text = '';
    
    switch (signalType) {
        case 'BULLISH_BREAKOUT':
            badgeClass += 'bullish';
            icon = '📈';
            text = 'Breakout';
            break;
        case 'BEARISH_BREAKOUT':
            badgeClass += 'bearish';
            icon = '📉';
            text = 'Breakdown';
            break;
        case 'VOLUME_SURGE':
            badgeClass += 'volume';
            icon = '📊';
            text = 'Volume';
            break;
        case 'PRICE_BREAKOUT':
            badgeClass += 'bullish';
            icon = '⚡';
            text = 'Price Move';
            break;
        default:
            badgeClass += 'neutral';
            icon = '⏸️';
            text = 'Neutral';
    }
    
    return `<span class="${badgeClass}">${icon} ${text}</span>`;
}

function getStrengthBar(strength) {
    const fillClass = strength >= 70 ? 'high' : strength >= 40 ? 'medium' : 'low';
    const width = Math.min(strength, 100);
    
    return `
        <div class="strength-bar">
            <div class="strength-fill ${fillClass}" style="width: ${width}%"></div>
        </div>
    `;
}

function getVolumeClass(ratio) {
    if (ratio >= 3.0) return 'volume-high';
    if (ratio >= 2.0) return 'volume-medium';
    return 'volume-low';
}

function getCryptoFullName(symbol) {
    const names = {
        'BTC': 'Bitcoin',
        'ETH': 'Ethereum',
        'SOL': 'Solana',
        'ADA': 'Cardano',
        'DOT': 'Polkadot',
        'BNB': 'BNB',
        'XRP': 'Ripple',
        'MATIC': 'Polygon',
        'LINK': 'Chainlink',
        'AVAX': 'Avalanche'
    };
    return names[symbol] || symbol;
}

function formatTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Now';
    if (diffMins < 60) return `${diffMins}m`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d`;
}

function updateScannerStatus() {
    const statusDot = document.getElementById('scanner-status-dot');
    const statusLabel = document.getElementById('scanner-status-label');
    const toggleBtn = document.getElementById('scanner-toggle-btn');
    
    if (scannerRunning) {
        statusDot.className = 'w-2 h-2 bg-green-500 rounded-full scanner-running';
        statusLabel.textContent = 'Scanner Running';
        statusLabel.className = 'text-sm text-green-400';
        toggleBtn.innerHTML = '<i class="fas fa-stop mr-2"></i>Stop Scanner';
        toggleBtn.className = 'bg-red-600 hover:bg-red-700 px-6 py-2 rounded-lg font-medium transition-colors text-white';
    } else {
        statusDot.className = 'w-2 h-2 bg-red-500 rounded-full scanner-stopped';
        statusLabel.textContent = 'Scanner Stopped';
        statusLabel.className = 'text-sm text-gray-400';
        toggleBtn.innerHTML = '<i class="fas fa-play mr-2"></i>Start Scanner';
        toggleBtn.className = 'bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg font-medium transition-colors text-white';
    }
}

function updateScannerStats() {
    // Update basic stats
    document.getElementById('total-scanned').textContent = watchlistSymbols.length;
    document.getElementById('breakout-count').textContent = breakoutSignals.filter(s => s.signal_type !== 'NEUTRAL').length;
    document.getElementById('bullish-count').textContent = scannerStats.bullishSignals;
    document.getElementById('bearish-count').textContent = scannerStats.bearishSignals;
    
    // Calculate success rate (placeholder - would need historical data for real calculation)
    const totalSignals = scannerStats.bullishSignals + scannerStats.bearishSignals;
    const successRate = totalSignals > 0 ? Math.round((scannerStats.bullishSignals / totalSignals) * 100) : 0;
    document.getElementById('success-rate').textContent = `${successRate}%`;
}

function updateLastScanTime() {
    // This function can be used to update last scan time if needed
    // For now, we'll show it in the scanner status
}

// Sorting Functions for CoinDCX-style interface
function sortBreakoutTable(sortBy) {
    switch (sortBy) {
        case 'rank':
        case 'strength':
            breakoutSignals.sort((a, b) => b.signal_strength - a.signal_strength);
            break;
        case 'volume':
            breakoutSignals.sort((a, b) => b.volume_ratio - a.volume_ratio);
            break;
        case 'price_desc':
            breakoutSignals.sort((a, b) => b.price - a.price);
            break;
        case 'price_asc':
            breakoutSignals.sort((a, b) => a.price - b.price);
            break;
        case 'change_desc':
            breakoutSignals.sort((a, b) => b.price_change_pct - a.price_change_pct);
            break;
        case 'change_asc':
            breakoutSignals.sort((a, b) => a.price_change_pct - b.price_change_pct);
            break;
    }
    updateBreakoutTable();
}

// Add event listeners for sorting
function initializeSortControls() {
    document.getElementById('sort-by-rank')?.addEventListener('change', (e) => {
        sortBreakoutTable(e.target.value);
    });
    
    document.getElementById('sort-by-price')?.addEventListener('change', (e) => {
        sortBreakoutTable(e.target.value);
    });
    
    document.getElementById('sort-by-change')?.addEventListener('change', (e) => {
        sortBreakoutTable(e.target.value);
    });
}

function addSymbolToWatchlist() {
    // For the CoinDCX-style interface, we'll add symbols programmatically
    // This function can be enhanced to add custom symbols if needed
    showNotification('Symbol management feature coming soon', 'info');
}

function clearScannerResults() {
    breakoutSignals = [];
    scannerStats = {
        totalBreakouts: 0,
        bullishSignals: 0,
        bearishSignals: 0,
        accuracyRate: 0
    };
    
    updateBreakoutTable();
    updateScannerStats();
    showNotification('Scanner results cleared', 'info');
}

function viewSignalDetails(symbol) {
    const signal = breakoutSignals.find(s => s.symbol === symbol);
    if (signal) {
        alert(`Signal Details for ${symbol}:\n\n${signal.signal_reason}\n\nStrength: ${signal.signal_strength}%\nPrice: $${signal.price.toFixed(4)}\nVolume Ratio: ${signal.volume_ratio.toFixed(1)}x`);
    }
}

// Helper Functions
function getSignalClass(signalType) {
    if (signalType.includes('BULLISH')) return 'signal-bullish';
    if (signalType.includes('BEARISH')) return 'signal-bearish';
    return 'signal-neutral';
}

function getStrengthClass(strength) {
    if (strength >= 70) return 'strength-high';
    if (strength >= 40) return 'strength-medium';
    return 'strength-low';
}

function formatSignalType(type) {
    return type.replace('_', ' ').toLowerCase().split(' ').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function getTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
}

// Make functions available globally
window.switchTab = switchTab;
window.switchMainView = switchMainView;
window.toggleBreakoutScanner = toggleBreakoutScanner;
window.addSymbolToWatchlist = addSymbolToWatchlist;
window.clearScannerResults = clearScannerResults;
window.sortBreakoutTable = sortBreakoutTable;

// Main View Switching
function switchMainView(viewName) {
    // Update navigation buttons
    document.querySelectorAll('.nav-button').forEach(btn => {
        btn.classList.remove('active');
        btn.classList.remove('bg-crypto-blue', 'text-white');
        btn.classList.add('text-gray-400');
    });
    
    // Update main view content
    document.querySelectorAll('.main-view').forEach(view => {
        view.classList.add('hidden');
    });
    
    // Activate selected view
    const activeBtn = document.getElementById(`nav-${viewName}`);
    const activeView = document.getElementById(`view-${viewName}`);
    
    if (activeBtn && activeView) {
        activeBtn.classList.add('active', 'bg-crypto-blue', 'text-white');
        activeBtn.classList.remove('text-gray-400');
        activeView.classList.remove('hidden');
    }
    
    // Initialize scanner if switching to scanner view
    if (viewName === 'scanner') {
        initializeScanner();
    }
}

function initializeScanner() {
    updateScannerTable();
    updateScannerStats();
}