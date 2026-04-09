/**
 * Rate Limit Handler for AJAX requests
 * Handles 429 responses from nginx rate limiting and provides user-friendly feedback
 */

class RateLimitHandler {
    constructor() {
        this.retryTimeouts = new Map();
        this.setupGlobalErrorHandler();
    }

    /**
     * Setup global error handler for AJAX requests
     */
    setupGlobalErrorHandler() {
        // Handle jQuery AJAX errors
        if (typeof $ !== 'undefined') {
            $(document).ajaxError((event, xhr, settings, thrownError) => {
                this.handleAjaxError(xhr, settings);
            });
        }

        // Handle fetch API errors
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            try {
                const response = await originalFetch(...args);
                if (response.status === 429) {
                    const data = await response.json();
                    this.handleRateLimitError(data, args[0]);
                }
                return response;
            } catch (error) {
                throw error;
            }
        };
    }

    /**
     * Handle AJAX error responses
     */
    handleAjaxError(xhr, settings) {
        if (xhr.status === 429) {
            try {
                const data = JSON.parse(xhr.responseText);
                this.handleRateLimitError(data, settings);
            } catch (e) {
                console.error('Failed to parse rate limit response:', e);
                this.showGenericRateLimitError();
            }
        }
    }

    /**
     * Handle rate limit error with retry information
     */
    handleRateLimitError(data, requestSettings) {
        if (data.is_rate_limit) {
            const retryAfter = data.retry_after || 60;
            const rateLimitType = data.rate_limit_type || 'general';
            const message = data.message || 'Rate limit exceeded. Please wait before trying again.';

            // Show rate limit notification
            this.showRateLimitNotification(message, retryAfter, rateLimitType);

            // Schedule automatic retry if it's a critical request
            if (this.shouldAutoRetry(requestSettings, rateLimitType)) {
                this.scheduleAutoRetry(requestSettings, retryAfter);
            }
        }
    }

    /**
     * Show rate limit notification to user
     */
    showRateLimitNotification(message, retryAfter, rateLimitType) {
        // Remove existing notifications
        this.removeExistingNotifications();

        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'rate-limit-notification alert alert-warning alert-dismissible fade show';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        `;

        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-clock me-2"></i>
                <div class="flex-grow-1">
                    <strong>Rate Limit Exceeded</strong>
                    <div class="small">${message}</div>
                    <div class="mt-2">
                        <div class="progress" style="height: 4px;">
                            <div class="progress-bar bg-warning" role="progressbar" style="width: 0%" id="rateLimitProgress"></div>
                        </div>
                        <small class="text-muted">Retry in <span id="rateLimitCountdown">${retryAfter}</span> seconds</span></small>
                    </div>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        document.body.appendChild(notification);

        // Start countdown
        this.startCountdown(notification, retryAfter);
    }

    /**
     * Start countdown timer for rate limit notification
     */
    startCountdown(notification, retryAfter) {
        let timeLeft = retryAfter;
        const countdownElement = notification.querySelector('#rateLimitCountdown');
        const progressBar = notification.querySelector('#rateLimitProgress');

        const updateCountdown = () => {
            countdownElement.textContent = timeLeft;
            const progress = ((retryAfter - timeLeft) / retryAfter) * 100;
            progressBar.style.width = progress + '%';

            if (timeLeft <= 0) {
                notification.remove();
                return;
            }

            timeLeft--;
            setTimeout(updateCountdown, 1000);
        };

        updateCountdown();
    }

    /**
     * Schedule automatic retry for critical requests
     */
    scheduleAutoRetry(requestSettings, retryAfter) {
        const requestKey = this.getRequestKey(requestSettings);
        
        // Clear existing timeout for this request
        if (this.retryTimeouts.has(requestKey)) {
            clearTimeout(this.retryTimeouts.get(requestKey));
        }

        // Schedule new retry
        const timeoutId = setTimeout(() => {
            this.retryRequest(requestSettings);
            this.retryTimeouts.delete(requestKey);
        }, retryAfter * 1000);

        this.retryTimeouts.set(requestKey, timeoutId);
    }

    /**
     * Retry the original request
     */
    retryRequest(requestSettings) {
        if (typeof $ !== 'undefined' && requestSettings.url) {
            // jQuery AJAX retry
            $.ajax(requestSettings).done((data) => {
                this.showSuccessNotification('Request completed successfully');
            }).fail((xhr) => {
                if (xhr.status === 429) {
                    // Still rate limited, show notification again
                    const responseData = JSON.parse(xhr.responseText);
                    this.handleRateLimitError(responseData, requestSettings);
                }
            });
        } else if (requestSettings && requestSettings.url) {
            // Fetch API retry
            fetch(requestSettings.url, requestSettings)
                .then(response => {
                    if (response.ok) {
                        this.showSuccessNotification('Request completed successfully');
                    } else if (response.status === 429) {
                        response.json().then(data => this.handleRateLimitError(data, requestSettings));
                    }
                })
                .catch(error => console.error('Retry failed:', error));
        }
    }

    /**
     * Determine if request should be auto-retried
     */
    shouldAutoRetry(requestSettings, rateLimitType) {
        // Don't auto-retry login attempts for security
        if (rateLimitType === 'login') {
            return false;
        }

        // Auto-retry critical API calls
        const criticalPaths = ['/api/kpi/', '/api/dashboard/', '/api/data/'];
        const url = requestSettings.url || '';
        
        return criticalPaths.some(path => url.includes(path));
    }

    /**
     * Generate unique key for request
     */
    getRequestKey(requestSettings) {
        return `${requestSettings.method || 'GET'}_${requestSettings.url || ''}`;
    }

    /**
     * Show success notification
     */
    showSuccessNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'alert alert-success alert-dismissible fade show';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 300px;
        `;

        notification.innerHTML = `
            <i class="fas fa-check-circle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }

    /**
     * Show generic rate limit error
     */
    showGenericRateLimitError() {
        this.showRateLimitNotification(
            'Rate limit exceeded. Please wait before trying again.',
            60,
            'general'
        );
    }

    /**
     * Remove existing rate limit notifications
     */
    removeExistingNotifications() {
        const existing = document.querySelectorAll('.rate-limit-notification');
        existing.forEach(notification => notification.remove());
    }

    /**
     * Clear all retry timeouts
     */
    clearAllRetries() {
        this.retryTimeouts.forEach(timeoutId => clearTimeout(timeoutId));
        this.retryTimeouts.clear();
    }
}

// Initialize rate limit handler when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.rateLimitHandler = new RateLimitHandler();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RateLimitHandler;
}



