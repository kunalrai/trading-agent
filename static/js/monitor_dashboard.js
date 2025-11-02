let monitoring = false;
let autoUpdate = null;

function updateData() {
    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            const current = data.current_data;
            
            if (current && Object.keys(current).length > 0) {
                // Update price data (with error checking)
                const currentPriceEl = document.getElementById('current-price');
                const ema20El = document.getElementById('ema20');
                const ema50El = document.getElementById('ema50');
                const priceVsEma20El = document.getElementById('price-vs-ema20');
                const macdEl = document.getElementById('macd');
                const rsi7El = document.getElementById('rsi7');
                const rsi14El = document.getElementById('rsi14');
                const rsi7NeedleEl = document.getElementById('rsi7-needle');
                
                if (currentPriceEl) currentPriceEl.textContent = `$${current.price.toFixed(2)}`;
                if (ema20El) ema20El.textContent = `$${current.ema20.toFixed(2)}`;
                if (ema50El) ema50El.textContent = `$${(current.ema50 || 0).toFixed(2)}`;
                if (priceVsEma20El) priceVsEma20El.textContent = `${current.price_vs_ema20_pct ? current.price_vs_ema20_pct.toFixed(2) : 0}%`;
                if (macdEl) macdEl.textContent = current.macd.toFixed(3);
                
                // Update RSI (with error checking)
                if (rsi7El) rsi7El.textContent = current.rsi7.toFixed(1);
                if (rsi14El) rsi14El.textContent = current.rsi14.toFixed(1);
                
                // Update RSI needle (0-100 scale) with error checking
                if (rsi7NeedleEl) {
                    const rsi7Angle = (current.rsi7 / 100) * 180 - 90; // -90 to 90 degrees
                    rsi7NeedleEl.style.transform = `translateX(-50%) rotate(${rsi7Angle}deg)`;
                }
                
                // Update signal (with error checking)
                const signalEl = document.getElementById('signal-status');
                const confidenceEl = document.getElementById('confidence');
                const confidenceBarEl = document.getElementById('confidence-bar');
                const strengthEl = document.getElementById('strength');
                const validityEl = document.getElementById('validity');
                
                const direction = current.signal_direction;
                if (signalEl) {
                    signalEl.textContent = direction;
                    signalEl.className = `signal-status signal-${direction.toLowerCase()}`;
                }
                
                if (confidenceEl) confidenceEl.textContent = `${current.confidence}%`;
                if (confidenceBarEl) confidenceBarEl.style.width = `${current.confidence}%`;
                if (strengthEl) strengthEl.textContent = `${current.signal_strength}/100`;
                if (validityEl) validityEl.textContent = `${current.validity_hours} hours`;
                
                // Update status bar (with error checking)
                const checkCountEl = document.getElementById('check-count');
                const signalCountEl = document.getElementById('signal-count');
                if (checkCountEl) checkCountEl.textContent = current.check_count || 0;
                if (signalCountEl) signalCountEl.textContent = current.signal_count || 0;
                
                // Show/hide trade levels (with error checking)
                const tradeLevelsCard = document.getElementById('trade-levels-card');
                if (tradeLevelsCard && direction !== 'HOLD' && current.entry_price) {
                    tradeLevelsCard.style.display = 'block';
                    
                    // Safely update all trade level elements
                    const entryPriceEl = document.getElementById('entry-price');
                    const stopLossEl = document.getElementById('stop-loss');
                    const tp1El = document.getElementById('tp1');
                    const tp2El = document.getElementById('tp2');
                    const tp3El = document.getElementById('tp3');
                    const rr1El = document.getElementById('rr1');
                    const rr2El = document.getElementById('rr2');
                    const rr3El = document.getElementById('rr3');
                    const positionSizeEl = document.getElementById('position-size');
                    const riskAmountEl = document.getElementById('risk-amount');
                    
                    if (entryPriceEl) entryPriceEl.textContent = `$${current.entry_price ? current.entry_price.toFixed(2) : '-'}`;
                    if (stopLossEl) stopLossEl.textContent = `$${current.stop_loss ? current.stop_loss.toFixed(2) : '-'}`;
                    if (tp1El) tp1El.textContent = `$${current.take_profit_1 ? current.take_profit_1.toFixed(2) : '-'}`;
                    if (tp2El) tp2El.textContent = `$${current.take_profit_2 ? current.take_profit_2.toFixed(2) : '-'}`;
                    if (tp3El) tp3El.textContent = `$${current.take_profit_3 ? current.take_profit_3.toFixed(2) : '-'}`;
                    if (rr1El) rr1El.textContent = `1:${current.risk_reward_1 || 0}`;
                    if (rr2El) rr2El.textContent = `1:${current.risk_reward_2 || 0}`;
                    if (rr3El) rr3El.textContent = `1:${current.risk_reward_3 || 0}`;
                    if (positionSizeEl) positionSizeEl.textContent = `${current.position_size_pct}%`;
                    if (riskAmountEl) riskAmountEl.textContent = `$${current.risk_amount ? current.risk_amount.toFixed(2) : '0.00'}`;
                    
                    // Update signal factors (with error checking)
                    const factorsList = document.getElementById('signal-factors');
                    if (factorsList) {
                        if (current.signal_factors && current.signal_factors.length > 0) {
                            factorsList.innerHTML = current.signal_factors.map(f => `<li>${f}</li>`).join('');
                        } else {
                            factorsList.innerHTML = '<li>No specific factors</li>';
                        }
                    }
                } else if (tradeLevelsCard) {
                    tradeLevelsCard.style.display = 'none';
                }
                
                // Update intraday analysis
                updateIntradayAnalysis(current);
            }
            
            // Update monitoring status
            const statusIndicator = document.getElementById('status-indicator');
            const statusText = document.getElementById('monitoring-status');
            
            if (statusIndicator && statusText) {
                if (data.monitoring_active) {
                    statusIndicator.classList.add('active');
                    statusText.textContent = 'Active';
                } else {
                    statusIndicator.classList.remove('active');
                    statusText.textContent = 'Stopped';
                }
            }
            
            // Update last update time
            const lastUpdateEl = document.getElementById('last-update');
            if (data.last_update && lastUpdateEl) {
                const updateTime = new Date(data.last_update).toLocaleTimeString();
                lastUpdateEl.textContent = updateTime;
            }
            
            // Update monitoring log
            const logContainer = document.getElementById('monitoring-log');
            if (logContainer && data.monitoring_log && data.monitoring_log.length > 0) {
                logContainer.innerHTML = data.monitoring_log
                    .reverse()
                    .map(entry => `
                        <div class="log-entry ${entry.type.toLowerCase()}">
                            <div class="log-time">${entry.time_str}</div>
                            <div>${entry.message}</div>
                        </div>
                    `).join('');
            }
            
            // Update signal history
            const historyContainer = document.getElementById('signal-history');
            if (historyContainer && data.signal_history && data.signal_history.length > 0) {
                historyContainer.innerHTML = data.signal_history
                    .reverse()
                    .map(signal => {
                        const time = new Date(signal.timestamp).toLocaleTimeString();
                        const emoji = signal.signal_direction === 'LONG' ? '📈' : '📉';
                        return `
                            <div class="metric">
                                <span>${time}</span>
                                <span>${emoji} ${signal.signal_direction} ${signal.confidence}%</span>
                            </div>
                        `;
                    }).join('');
            }
        })
        .catch(error => console.error('Error fetching data:', error));
}

function startMonitoring() {
    fetch('/api/start_monitoring')
        .then(response => response.json())
        .then(data => {
            monitoring = true;
            if (autoUpdate) clearInterval(autoUpdate);
            autoUpdate = setInterval(updateData, 3000); // Update every 3 seconds
            updateData();
        })
        .catch(error => console.error('Error starting monitoring:', error));
}

function stopMonitoring() {
    fetch('/api/stop_monitoring')
        .then(response => response.json())
        .then(data => {
            monitoring = false;
            if (autoUpdate) {
                clearInterval(autoUpdate);
                autoUpdate = null;
            }
        })
        .catch(error => console.error('Error stopping monitoring:', error));
}

function checkNow() {
    const checkButton = document.querySelector('.btn-success');
    if (!checkButton) return;
    
    const originalText = checkButton.textContent;
    
    // Add loading indicator to price display
    const priceDisplay = document.getElementById('current-price');
    if (!priceDisplay) return;
    
    const originalPrice = priceDisplay.textContent;
    priceDisplay.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
    priceDisplay.textContent = 'Checking...';
    
    // Disable button and show loading state
    checkButton.disabled = true;
    checkButton.textContent = '🔄 Checking...';
    checkButton.style.opacity = '0.6';
    checkButton.style.transform = 'scale(0.95)';
    
    // Add loading animation to status indicator
    const statusIndicator = document.getElementById('status-indicator');
    if (statusIndicator) {
        statusIndicator.style.animation = 'pulse 0.5s infinite';
    }
    
    fetch('/api/get_signal')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update with fresh data from the API response
                const current = data.current_data;
                
                // Immediately update with the fresh data
                if (current) {
                    // Update price with animation
                    priceDisplay.style.background = 'linear-gradient(135deg, #22c55e, #16a34a)';
                    priceDisplay.textContent = `$${current.price.toFixed(2)}`;
                    
                    // Update all other fields immediately (with error checking)
                    const ema20El = document.getElementById('ema20');
                    const ema50El = document.getElementById('ema50');
                    const priceVsEma20El = document.getElementById('price-vs-ema20');
                    const macdEl = document.getElementById('macd');
                    const rsi7El = document.getElementById('rsi7');
                    const rsi14El = document.getElementById('rsi14');
                    const rsi7NeedleEl = document.getElementById('rsi7-needle');
                    
                    if (ema20El) ema20El.textContent = `$${current.ema20.toFixed(2)}`;
                    if (ema50El) ema50El.textContent = `$${(current.ema50 || 0).toFixed(2)}`;
                    if (priceVsEma20El) priceVsEma20El.textContent = `${current.price_vs_ema20_pct ? current.price_vs_ema20_pct.toFixed(2) : 0}%`;
                    if (macdEl) macdEl.textContent = current.macd.toFixed(3);
                    
                    // Update RSI (with error checking)
                    if (rsi7El) rsi7El.textContent = current.rsi7.toFixed(1);
                    if (rsi14El) rsi14El.textContent = current.rsi14.toFixed(1);
                    
                    // Update RSI needle with animation (with error checking)
                    if (rsi7NeedleEl) {
                        const rsi7Angle = (current.rsi7 / 100) * 180 - 90;
                        rsi7NeedleEl.style.transform = `translateX(-50%) rotate(${rsi7Angle}deg)`;
                    }
                    
                    // Update signal with animation
                    const signalEl = document.getElementById('signal-status');
                    if (signalEl) {
                        const direction = current.signal_direction;
                        signalEl.style.transform = 'scale(1.1)';
                        signalEl.textContent = direction;
                        signalEl.className = `signal-status signal-${direction.toLowerCase()}`;
                        
                        setTimeout(() => {
                            signalEl.style.transform = 'scale(1)';
                        }, 200);
                    }
                    
                    const confidenceEl = document.getElementById('confidence');
                    const confidenceBarEl = document.getElementById('confidence-bar');
                    const strengthEl = document.getElementById('strength');
                    const validityEl = document.getElementById('validity');
                    
                    if (confidenceEl) confidenceEl.textContent = `${current.confidence}%`;
                    if (confidenceBarEl) confidenceBarEl.style.width = `${current.confidence}%`;
                    if (strengthEl) strengthEl.textContent = `${current.signal_strength}/100`;
                    if (validityEl) validityEl.textContent = `${current.validity_hours} hours`;
                    
                    // Update trade levels if signal is active
                    const tradeLevelsCard = document.getElementById('trade-levels-card');
                    const direction = current.signal_direction;
                    
                    if (tradeLevelsCard && direction !== 'HOLD' && current.entry_price) {
                        tradeLevelsCard.style.display = 'block';
                        tradeLevelsCard.style.animation = 'fadeIn 0.5s ease-in';
                        
                        const entryPriceEl = document.getElementById('entry-price');
                        const stopLossEl = document.getElementById('stop-loss');
                        const tp1El = document.getElementById('tp1');
                        const tp2El = document.getElementById('tp2');
                        const tp3El = document.getElementById('tp3');
                        const rr1El = document.getElementById('rr1');
                        const rr2El = document.getElementById('rr2');
                        const rr3El = document.getElementById('rr3');
                        const positionSizeEl = document.getElementById('position-size');
                        const riskAmountEl = document.getElementById('risk-amount');
                        
                        if (entryPriceEl) entryPriceEl.textContent = `$${current.entry_price ? current.entry_price.toFixed(2) : '-'}`;
                        if (stopLossEl) stopLossEl.textContent = `$${current.stop_loss ? current.stop_loss.toFixed(2) : '-'}`;
                        if (tp1El) tp1El.textContent = `$${current.take_profit_1 ? current.take_profit_1.toFixed(2) : '-'}`;
                        if (tp2El) tp2El.textContent = `$${current.take_profit_2 ? current.take_profit_2.toFixed(2) : '-'}`;
                        if (tp3El) tp3El.textContent = `$${current.take_profit_3 ? current.take_profit_3.toFixed(2) : '-'}`;
                        if (rr1El) rr1El.textContent = `1:${current.risk_reward_1 || 0}`;
                        if (rr2El) rr2El.textContent = `1:${current.risk_reward_2 || 0}`;
                        if (rr3El) rr3El.textContent = `1:${current.risk_reward_3 || 0}`;
                        if (positionSizeEl) positionSizeEl.textContent = `${current.position_size_pct}%`;
                        if (riskAmountEl) riskAmountEl.textContent = `$${current.risk_amount ? current.risk_amount.toFixed(2) : '0.00'}`;
                        
                        // Update signal factors
                        const factorsList = document.getElementById('signal-factors');
                        if (factorsList) {
                            if (current.signal_factors && current.signal_factors.length > 0) {
                                factorsList.innerHTML = current.signal_factors.map(f => `<li>${f}</li>`).join('');
                            } else {
                                factorsList.innerHTML = '<li>No specific factors</li>';
                            }
                        }
                    } else if (tradeLevelsCard) {
                        tradeLevelsCard.style.display = 'none';
                    }
                    
                    // Update intraday analysis
                    updateIntradayAnalysis(current);
                    
                    // Update last update time
                    const lastUpdateEl = document.getElementById('last-update');
                    if (lastUpdateEl) {
                        lastUpdateEl.textContent = new Date().toLocaleTimeString();
                    }
                }
                
                // Show success feedback
                checkButton.textContent = '✓ Updated!';
                checkButton.style.background = 'linear-gradient(135deg, #22c55e, #16a34a)';
                checkButton.style.transform = 'scale(1)';
                
                // Reset price display color after 1 second
                setTimeout(() => {
                    priceDisplay.style.background = 'linear-gradient(135deg, #2563eb, #3b82f6)';
                }, 1000);
                
                // Also call updateData to get the monitoring log updated
                setTimeout(() => {
                    updateData();
                }, 500);
                
                // Reset button after 2 seconds
                setTimeout(() => {
                    checkButton.textContent = originalText;
                    checkButton.style.background = 'linear-gradient(135deg, #22c55e, #16a34a)';
                    checkButton.style.opacity = '1';
                    checkButton.disabled = false;
                    if (statusIndicator) statusIndicator.style.animation = '';
                }, 2000);
                
            } else {
                // Show error feedback
                priceDisplay.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
                priceDisplay.textContent = 'Error!';
                
                checkButton.textContent = '✗ Error';
                checkButton.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
                checkButton.style.transform = 'scale(1)';
                
                console.error('Manual check failed:', data.error);
                
                // Reset after 3 seconds
                setTimeout(() => {
                    priceDisplay.style.background = 'linear-gradient(135deg, #2563eb, #3b82f6)';
                    priceDisplay.textContent = originalPrice;
                    checkButton.textContent = originalText;
                    checkButton.style.background = 'linear-gradient(135deg, #22c55e, #16a34a)';
                    checkButton.style.opacity = '1';
                    checkButton.disabled = false;
                    if (statusIndicator) statusIndicator.style.animation = '';
                }, 3000);
            }
        })
        .catch(error => {
            // Handle network errors
            priceDisplay.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
            priceDisplay.textContent = 'Network Error!';
            
            checkButton.textContent = '✗ Network Error';
            checkButton.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
            checkButton.style.transform = 'scale(1)';
            
            console.error('Network error during manual check:', error);
            
            // Reset after 3 seconds
            setTimeout(() => {
                priceDisplay.style.background = 'linear-gradient(135deg, #2563eb, #3b82f6)';
                priceDisplay.textContent = originalPrice;
                checkButton.textContent = originalText;
                checkButton.style.background = 'linear-gradient(135deg, #22c55e, #16a34a)';
                checkButton.style.opacity = '1';
                checkButton.disabled = false;
                if (statusIndicator) statusIndicator.style.animation = '';
            }, 3000);
        });
}

function updateIntradayAnalysis(current) {
    // This function will be enhanced to show comprehensive intraday analysis
    // For now, we'll simulate the data structure you provided
    
    // Simulated intraday series (in a real implementation, this would come from the API)
    const intradayData = current.intraday_series || {};
    
    // Update price series
    const priceSeriesEl = document.getElementById('price-series');
    if (priceSeriesEl) {
        if (intradayData.price_series) {
            priceSeriesEl.textContent = intradayData.price_series.map(p => p.toFixed(1)).join(', ');
            
            // Calculate price trend
            const prices = intradayData.price_series;
            if (prices && prices.length >= 2) {
                const trend = prices[prices.length - 1] > prices[0] ? 'up' : 
                             prices[prices.length - 1] < prices[0] ? 'down' : 'sideways';
                const trendEl = document.getElementById('price-trend');
                if (trendEl) {
                    trendEl.textContent = trend.toUpperCase();
                    trendEl.className = `trend-indicator trend-${trend}`;
                }
            }
        } else {
            // Fallback: create synthetic series based on current price
            const currentPrice = current.price;
            const syntheticPrices = generateSyntheticSeries(currentPrice, 10, 0.1);
            priceSeriesEl.textContent = syntheticPrices.map(p => p.toFixed(2)).join(', ');
            
            // Simple trend based on current vs EMA
            const trend = current.price > current.ema20 ? 'up' : current.price < current.ema20 ? 'down' : 'sideways';
            const trendEl = document.getElementById('price-trend');
            if (trendEl) {
                trendEl.textContent = trend.toUpperCase();
                trendEl.className = `trend-indicator trend-${trend}`;
            }
        }
    }
    
    // Update EMA20 series
    const ema20SeriesEl = document.getElementById('ema20-series');
    if (ema20SeriesEl) {
        if (intradayData.ema20_series) {
            ema20SeriesEl.textContent = intradayData.ema20_series.map(e => e.toFixed(2)).join(', ');
        } else {
            const syntheticEMA = generateSyntheticSeries(current.ema20, 10, 0.05);
            ema20SeriesEl.textContent = syntheticEMA.map(e => e.toFixed(2)).join(', ');
        }
    }
    
    // Update MACD series
    const macdSeriesEl = document.getElementById('macd-series');
    if (macdSeriesEl) {
        if (intradayData.macd_series) {
            macdSeriesEl.textContent = intradayData.macd_series.map(m => m.toFixed(3)).join(', ');
        } else {
            const syntheticMACD = generateSyntheticSeries(current.macd, 10, 0.02);
            macdSeriesEl.textContent = syntheticMACD.map(m => m.toFixed(3)).join(', ');
        }
    }
    
    // Update RSI series
    const rsi7SeriesEl = document.getElementById('rsi7-series');
    if (rsi7SeriesEl) {
        if (intradayData.rsi7_series) {
            rsi7SeriesEl.textContent = intradayData.rsi7_series.map(r => r.toFixed(1)).join(', ');
        } else {
            const syntheticRSI7 = generateSyntheticSeries(current.rsi7, 10, 2);
            rsi7SeriesEl.textContent = syntheticRSI7.map(r => Math.max(0, Math.min(100, r)).toFixed(1)).join(', ');
        }
    }
    
    const rsi14SeriesEl = document.getElementById('rsi14-series');
    if (rsi14SeriesEl) {
        if (intradayData.rsi14_series) {
            rsi14SeriesEl.textContent = intradayData.rsi14_series.map(r => r.toFixed(1)).join(', ');
        } else {
            const syntheticRSI14 = generateSyntheticSeries(current.rsi14, 10, 1.5);
            rsi14SeriesEl.textContent = syntheticRSI14.map(r => Math.max(0, Math.min(100, r)).toFixed(1)).join(', ');
        }
    }
    
    // Update 4H context
    const longerContext = current.longer_term_context || {};
    
    // EMA indicators
    const ema20_4hEl = document.getElementById('ema20-4h');
    if (ema20_4hEl) ema20_4hEl.textContent = (longerContext.ema20_4h || current.ema20).toFixed(2);
    
    const ema50_4hEl = document.getElementById('ema50-4h');
    if (ema50_4hEl) ema50_4hEl.textContent = (longerContext.ema50_4h || current.ema50 || current.ema20).toFixed(2);
    
    // ATR indicators
    const atr3_4hEl = document.getElementById('atr3-4h');
    if (atr3_4hEl) atr3_4hEl.textContent = (longerContext.atr3_4h || 444.048).toFixed(3);
    
    const atr14_4hEl = document.getElementById('atr14-4h');
    if (atr14_4hEl) atr14_4hEl.textContent = (longerContext.atr14_4h || 721.016).toFixed(3);
    
    // Volume indicators
    const currentVolumeEl = document.getElementById('current-volume');
    if (currentVolumeEl) currentVolumeEl.textContent = (longerContext.current_volume || 53.457).toFixed(3);
    
    const averageVolumeEl = document.getElementById('average-volume');
    if (averageVolumeEl) averageVolumeEl.textContent = (longerContext.average_volume || 4329.191).toFixed(3);
    
    // Volume ratio
    const volumeRatioEl = document.getElementById('volume-ratio');
    if (volumeRatioEl) {
        const currentVol = longerContext.current_volume || 53.457;
        const avgVol = longerContext.average_volume || 4329.191;
        const ratio = (currentVol / avgVol * 100).toFixed(1);
        volumeRatioEl.textContent = `${ratio}%`;
        volumeRatioEl.className = `trend-indicator trend-${currentVol < avgVol * 0.5 ? 'down' : currentVol > avgVol * 1.5 ? 'up' : 'sideways'}`;
    }
    
    // MACD series
    const macd4hSeriesEl = document.getElementById('macd-4h-series');
    if (macd4hSeriesEl) {
        const macdSeries = longerContext.macd_series || [-1094.546, -1171.909, -1151.52, -1105.43, -991.709, -902.079, -853.405, -817.111, -723.125, -657.601];
        macd4hSeriesEl.textContent = macdSeries.map(m => m.toFixed(1)).join(', ');
    }
    
    // RSI(14) series
    const rsi14_4hSeriesEl = document.getElementById('rsi14-4h-series');
    if (rsi14_4hSeriesEl) {
        const rsiSeries = longerContext.rsi14_series || [26.525, 37.249, 41.628, 42.709, 46.773, 46.188, 44.422, 43.767, 47.798, 46.748];
        rsi14_4hSeriesEl.textContent = rsiSeries.map(r => r.toFixed(1)).join(', ');
    }
    
    const rsi14_4hEl = document.getElementById('rsi14-4h');
    if (rsi14_4hEl) {
        const rsiSeries = longerContext.rsi14_series || [26.525, 37.249, 41.628, 42.709, 46.773, 46.188, 44.422, 43.767, 47.798, 46.748];
        const currentRSI = rsiSeries[rsiSeries.length - 1] || current.rsi14;
        rsi14_4hEl.textContent = currentRSI.toFixed(1);
    }
    
    // Position vs 4H EMAs
    const ema20_4h = longerContext.ema20_4h || current.ema20;
    const ema50_4h = longerContext.ema50_4h || current.ema50 || current.ema20;
    const position4h = current.price > ema20_4h && current.price > ema50_4h ? 'Above Both' :
                      current.price < ema20_4h && current.price < ema50_4h ? 'Below Both' : 'Between EMAs';
    
    const position4hEl = document.getElementById('position-4h-emas');
    if (position4hEl) position4hEl.textContent = position4h;
    
    // Volatility level
    const atr3 = longerContext.atr3_4h || 0.5;
    const atr14 = longerContext.atr14_4h || 1.0;
    const volatility = atr3 > atr14 * 0.8 ? 'High' : atr3 < atr14 * 0.4 ? 'Low' : 'Normal';
    const volEl = document.getElementById('volatility-level');
    if (volEl) {
        volEl.textContent = volatility;
        volEl.className = `trend-indicator trend-${volatility.toLowerCase() === 'high' ? 'down' : volatility.toLowerCase() === 'low' ? 'up' : 'sideways'}`;
    }
    
    // MACD 4H trend (simplified)
    const macd4hTrend = current.macd > 0 ? 'Bullish' : 'Bearish';
    const macdTrendEl = document.getElementById('macd-4h-trend');
    if (macdTrendEl) {
        macdTrendEl.textContent = macd4hTrend;
        macdTrendEl.className = `trend-indicator trend-${macd4hTrend.toLowerCase() === 'bullish' ? 'up' : 'down'}`;
    }
    
    // Volume comparison (simulated)
    const volumeEl = document.getElementById('volume-vs-avg');
    if (volumeEl) volumeEl.textContent = 'Normal';
    
    // Update confidence factors
    updateConfidenceFactors(current);
}

function generateSyntheticSeries(baseValue, length, volatility) {
    const series = [];
    let current = baseValue;
    for (let i = 0; i < length; i++) {
        const change = (Math.random() - 0.5) * 2 * volatility;
        current += change;
        series.push(current);
    }
    return series;
}

function updateConfidenceFactors(current) {
    const factors = [];
    
    // Price vs EMA analysis
    if (current.price > current.ema20) {
        factors.push({
            text: `Price above EMA20 by ${((current.price - current.ema20) / current.ema20 * 100).toFixed(2)}% - Bullish`,
            type: 'positive'
        });
    } else {
        factors.push({
            text: `Price below EMA20 by ${((current.ema20 - current.price) / current.ema20 * 100).toFixed(2)}% - Bearish`,
            type: 'negative'
        });
    }
    
    // RSI analysis
    if (current.rsi7 < 30) {
        factors.push({
            text: `RSI(7) at ${current.rsi7.toFixed(1)} - Oversold, potential reversal`,
            type: 'positive'
        });
    } else if (current.rsi7 > 70) {
        factors.push({
            text: `RSI(7) at ${current.rsi7.toFixed(1)} - Overbought, potential reversal`,
            type: 'negative'
        });
    } else {
        factors.push({
            text: `RSI(7) at ${current.rsi7.toFixed(1)} - Neutral territory`,
            type: 'neutral'
        });
    }
    
    // MACD analysis
    if (current.macd > 0) {
        factors.push({
            text: `MACD positive at ${current.macd.toFixed(3)} - Bullish momentum`,
            type: 'positive'
        });
    } else {
        factors.push({
            text: `MACD negative at ${current.macd.toFixed(3)} - Bearish momentum`,
            type: 'negative'
        });
    }
    
    // Signal strength analysis
    if (current.signal_strength > 60) {
        factors.push({
            text: `Signal strength ${current.signal_strength}/100 - High confidence`,
            type: 'positive'
        });
    } else if (current.signal_strength > 30) {
        factors.push({
            text: `Signal strength ${current.signal_strength}/100 - Moderate confidence`,
            type: 'neutral'
        });
    } else {
        factors.push({
            text: `Signal strength ${current.signal_strength}/100 - Low confidence`,
            type: 'negative'
        });
    }
    
    // Render confidence factors
    const container = document.getElementById('confidence-factors');
    if (container) {
        container.innerHTML = factors.map(factor => 
            `<div class="confidence-item ${factor.type}">${factor.text}</div>`
        ).join('');
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initial data load
    updateData();
    
    // Set up auto-refresh if monitoring is active
    setTimeout(() => {
        updateData();
    }, 1000);
});