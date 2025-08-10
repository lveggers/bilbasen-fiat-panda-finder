/**
 * Main JavaScript for Bilbasen Fiat Panda Finder
 */

// Global app configuration
const App = {
    endpoints: {
        scrape: '/api/v1/scrape',
        scrapeSync: '/api/v1/scrape/sync',
        rescore: '/api/v1/rescore',
        dashboardData: '/api/dashboard-data'
    }
};

// Utility functions
const Utils = {
    formatPrice: (price) => {
        if (!price) return 'N/A';
        return new Intl.NumberFormat('da-DK', {
            style: 'currency',
            currency: 'DKK',
            minimumFractionDigits: 0
        }).format(price);
    },

    formatNumber: (num) => {
        if (!num) return 'N/A';
        return new Intl.NumberFormat('da-DK').format(num);
    },

    formatScore: (score) => {
        if (score === null || score === undefined) return 'No score';
        return score.toString();
    },

    getScoreClass: (score) => {
        if (!score) return 'bg-gray-900 text-gray-200';
        if (score >= 80) return 'bg-green-900 text-green-200';
        if (score >= 60) return 'bg-yellow-900 text-yellow-200';
        if (score >= 40) return 'bg-orange-900 text-orange-200';
        return 'bg-red-900 text-red-200';
    },

    showNotification: (message, type = 'info') => {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-md shadow-lg z-50 ${
            type === 'success' ? 'bg-green-600' :
            type === 'error' ? 'bg-red-600' :
            type === 'warning' ? 'bg-yellow-600' :
            'bg-blue-600'
        } text-white`;
        
        notification.innerHTML = `
            <div class="flex items-center">
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" 
                        class="ml-4 text-white hover:text-gray-200">
                    ×
                </button>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    },

    showLoading: (element, show = true) => {
        if (show) {
            element.disabled = true;
            element.innerHTML = `
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Loading...
            `;
        } else {
            element.disabled = false;
        }
    }
};

// API functions
const API = {
    async scrapeListings(maxPages = 3, includeDetails = true, sync = false) {
        const endpoint = sync ? App.endpoints.scrapeSync : App.endpoints.scrape;
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                max_pages: maxPages,
                include_details: includeDetails
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    },

    async rescoreListings() {
        const response = await fetch(App.endpoints.rescore, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    },

    async getDashboardData() {
        const response = await fetch(App.endpoints.dashboardData);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }
};

// Dashboard functions
const Dashboard = {
    async refreshData() {
        try {
            const data = await API.getDashboardData();
            
            // Update stats
            this.updateStats(data);
            
            // Update charts
            this.updateCharts(data);
            
            // Update listings table
            this.updateListingsTable(data.top_listings);
            
            Utils.showNotification('Dashboard updated successfully!', 'success');
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
            Utils.showNotification('Failed to refresh dashboard data', 'error');
        }
    },

    updateStats(data) {
        // Update total listings
        const totalElement = document.querySelector('[data-stat="total"]');
        if (totalElement) {
            totalElement.textContent = Utils.formatNumber(data.total_listings);
        }

        // Update average score
        const avgElement = document.querySelector('[data-stat="average"]');
        if (avgElement && data.score_stats) {
            avgElement.textContent = data.score_stats.mean_score.toFixed(1);
        }

        // Update max score
        const maxElement = document.querySelector('[data-stat="max"]');
        if (maxElement && data.score_stats) {
            maxElement.textContent = data.score_stats.max_score;
        }
    },

    updateCharts(data) {
        // Update histogram
        if (data.all_scores && data.all_scores.length > 0) {
            const histogramData = [{
                x: data.all_scores,
                type: 'histogram',
                nbinsx: 20,
                marker: {
                    color: '#3b82f6',
                    opacity: 0.7
                }
            }];

            const histogramLayout = {
                title: { text: 'Score Distribution', font: { color: '#ffffff' } },
                xaxis: { title: 'Score', color: '#9ca3af' },
                yaxis: { title: 'Count', color: '#9ca3af' },
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#ffffff' }
            };

            Plotly.redraw('score-histogram', histogramData, histogramLayout);
        }

        // Update score ranges chart
        if (data.score_stats && data.score_stats.score_ranges) {
            const pieData = [{
                values: Object.values(data.score_stats.score_ranges),
                labels: Object.keys(data.score_stats.score_ranges),
                type: 'pie',
                marker: {
                    colors: ['#ef4444', '#f97316', '#eab308', '#22c55e', '#10b981']
                }
            }];

            const pieLayout = {
                title: { text: 'Listings by Score Range', font: { color: '#ffffff' } },
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#ffffff' }
            };

            Plotly.redraw('score-ranges', pieData, pieLayout);
        }
    },

    updateListingsTable(listings) {
        const tableBody = document.querySelector('#listings-table tbody');
        if (!tableBody) return;

        if (!listings || listings.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="px-6 py-8 text-center text-gray-400">
                        No listings found
                    </td>
                </tr>
            `;
            return;
        }

        const html = listings.map((listing, index) => `
            <tr class="hover:bg-gray-750 transition-colors">
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center justify-center h-6 w-6 rounded-full bg-primary-600 text-white text-xs font-medium">
                        ${index + 1}
                    </span>
                </td>
                <td class="px-6 py-4">
                    <div class="text-sm text-white font-medium max-w-xs truncate" title="${listing.title}">
                        ${listing.title}
                    </div>
                    ${listing.location ? `<div class="text-xs text-gray-400">📍 ${listing.location}</div>` : ''}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${Utils.getScoreClass(listing.score)}">
                        ${Utils.formatScore(listing.score)}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    ${Utils.formatPrice(listing.price_dkk)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    ${listing.year || 'N/A'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    ${listing.kilometers ? Utils.formatNumber(listing.kilometers) + ' km' : 'N/A'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    ${listing.condition_str || 'Unknown'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <a href="${listing.url}" target="_blank" 
                       class="text-primary-400 hover:text-primary-300 transition-colors">
                        View →
                    </a>
                </td>
            </tr>
        `).join('');

        tableBody.innerHTML = html;
    }
};

// Global action functions (called from HTML)
window.triggerScraping = async function() {
    if (!confirm('This will scrape new listings from Bilbasen.dk. This may take a few minutes. Continue?')) {
        return;
    }

    const button = event.target;
    const originalText = button.innerHTML;
    
    try {
        Utils.showLoading(button);
        
        const result = await API.scrapeListings(3, true, false);
        
        Utils.showNotification('Scraping started! The page will refresh automatically when complete.', 'success');
        
        // Refresh page after 30 seconds for async scraping
        setTimeout(() => {
            window.location.reload();
        }, 30000);
        
    } catch (error) {
        console.error('Error:', error);
        Utils.showNotification('Failed to start scraping. Please try again.', 'error');
        button.innerHTML = originalText;
        button.disabled = false;
    }
};

window.rescoreListings = async function() {
    if (!confirm('Recalculate all listing scores? This may take a moment.')) {
        return;
    }

    const button = event.target;
    const originalText = button.innerHTML;
    
    try {
        Utils.showLoading(button);
        
        const result = await API.rescoreListings();
        
        Utils.showNotification(`Rescored ${result.updated_count} listings!`, 'success');
        
        // Refresh the page to show updated scores
        setTimeout(() => {
            window.location.reload();
        }, 1000);
        
    } catch (error) {
        console.error('Error:', error);
        Utils.showNotification('Failed to rescore listings. Please try again.', 'error');
        button.innerHTML = originalText;
        button.disabled = false;
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Bilbasen Fiat Panda Finder loaded');
    
    // Set up any initial event listeners or data loading here
    
    // Auto-refresh dashboard data every 5 minutes
    setInterval(() => {
        if (window.location.pathname === '/') {
            Dashboard.refreshData();
        }
    }, 5 * 60 * 1000);
});