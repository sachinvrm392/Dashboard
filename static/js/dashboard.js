/**
 * Number formatting function
 * Returns comma-separated string (e.g., 1,234,567)
 */
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return Number(num).toLocaleString('en-US');
}

/**
 * Helper to get CSRF token from cookies
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', function() {
    
    // 4. Progress bar color logic
    const progressBars = document.querySelectorAll('.usage-progress');
    progressBars.forEach(function(bar) {
        const percentage = parseFloat(bar.getAttribute('data-percentage') || 0);
        if (percentage < 60) {
            bar.classList.add('usage-low');
        } else if (percentage <= 80) {
            bar.classList.add('usage-medium');
        } else {
            bar.classList.add('usage-high');
        }
    });

    // 6. Auto-dismiss messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alertElement) {
        setTimeout(function() {
            // Check if bootstrap is available
            if (typeof bootstrap !== 'undefined') {
                const bsAlert = new bootstrap.Alert(alertElement);
                bsAlert.close();
            } else {
                alertElement.style.display = 'none';
            }
        }, 5000);
    });

    // 7. Number animation (optional nice touch)
    const animElements = document.querySelectorAll('.card-value');
    animElements.forEach(function(el) {
        const targetText = el.textContent.replace(/,/g, '');
        const target = parseFloat(targetText);
        
        if (!isNaN(target) && target > 0) {
            let current = 0;
            const steps = 30;
            const increment = target / steps;
            
            const updateCounter = () => {
                current += increment;
                if (current < target) {
                    el.textContent = formatNumber(Math.ceil(current));
                    requestAnimationFrame(updateCounter);
                } else {
                    el.textContent = formatNumber(target);
                }
            };
            updateCounter();
        }
    });

    // 2. Usage Chart initialization
    const usageChartCanvas = document.getElementById('usageChart');
    if (usageChartCanvas) {
        const dataElement = document.getElementById('usageChartData');
        if (dataElement) {
            try {
                const chartData = JSON.parse(dataElement.textContent);
                new Chart(usageChartCanvas, {
                    type: 'line',
                    data: {
                        labels: chartData.labels,
                        datasets: [{
                            label: 'Characters Used',
                            data: chartData.values,
                            borderColor: '#0d6efd',
                            backgroundColor: 'rgba(13, 110, 253, 0.1)',
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return formatNumber(context.raw) + ' chars';
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (e) {
                console.error("Error parsing usage chart data", e);
            }
        }
    }

    // 3. Breakdown Chart initialization
    const breakdownChartCanvas = document.getElementById('breakdownChart');
    if (breakdownChartCanvas) {
        const bdDataElement = document.getElementById('breakdownChartData');
        if (bdDataElement) {
            try {
                const bdData = JSON.parse(bdDataElement.textContent);
                new Chart(breakdownChartCanvas, {
                    type: 'doughnut',
                    data: {
                        labels: bdData.labels,
                        datasets: [{
                            data: bdData.values,
                            backgroundColor: [
                                '#0d6efd', '#198754', '#ffc107', '#dc3545', '#6f42c1', '#0dcaf0'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom'
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return context.label + ': ' + formatNumber(context.raw);
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (e) {
                console.error("Error parsing breakdown chart data", e);
            }
        }
    }

    // 5. Refresh button handler
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Show spinner
            const originalHtml = refreshBtn.innerHTML;
            refreshBtn.innerHTML = '<div class="spinner-border text-light spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div>';
            refreshBtn.disabled = true;

            const csrfToken = getCookie('csrftoken');
            
            fetch('/dashboard/api/refresh/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => {
                if (response.ok) {
                    window.location.reload();
                } else {
                    throw new Error('Refresh failed with status: ' + response.status);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // Reset button on error
                refreshBtn.innerHTML = originalHtml;
                refreshBtn.disabled = false;
                
                // Show error toast or alert
                alert('Failed to refresh data. Please try again.');
            });
        });
    }
});
