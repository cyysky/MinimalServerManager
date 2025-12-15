// API Service for frontend-backend communication
const API_BASE_URL = 'http://localhost:8000';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.retryAttempts = 3;
    this.retryDelay = 1000; // 1 second
  }

  // Generic request method with retry logic
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    let lastError;
    
    for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
      try {
        const response = await fetch(url, config);
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorMessage = errorData.detail || errorData.message || `HTTP error! status: ${response.status}`;
          
          // Don't retry on client errors (4xx)
          if (response.status >= 400 && response.status < 500) {
            throw new Error(errorMessage);
          }
          
          // Retry on server errors (5xx) or network issues
          if (attempt < this.retryAttempts) {
            console.warn(`Request failed (attempt ${attempt}/${this.retryAttempts}):`, errorMessage);
            await this.delay(this.retryDelay * attempt);
            continue;
          }
          
          throw new Error(errorMessage);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return await response.json();
        }
        
        return await response.text();
      } catch (error) {
        lastError = error;
        console.error(`API request failed (attempt ${attempt}/${this.retryAttempts}):`, error);
        
        // Don't retry on certain types of errors
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
          // Network error - can retry
          if (attempt < this.retryAttempts) {
            await this.delay(this.retryDelay * attempt);
            continue;
          }
        }
        
        // For other errors, don't retry
        break;
      }
    }
    
    console.error('All retry attempts failed');
    throw lastError;
  }

  // Helper method to add delay between retries
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Server CRUD operations
  async getServers() {
    return this.request('/servers/');
  }

  async getServer(serverId) {
    return this.request(`/servers/${serverId}`);
  }

  async createServer(serverData) {
    return this.request('/servers/', {
      method: 'POST',
      body: JSON.stringify(serverData),
    });
  }

  async updateServer(serverId, serverData) {
    return this.request(`/servers/${serverId}`, {
      method: 'PUT',
      body: JSON.stringify(serverData),
    });
  }

  async deleteServer(serverId) {
    return this.request(`/servers/${serverId}`, {
      method: 'DELETE',
    });
  }

  async toggleServerStatus(serverId) {
    return this.request(`/servers/${serverId}/toggle`, {
      method: 'POST',
    });
  }

  // Server monitoring
  async startMonitoring(serverId) {
    return this.request(`/servers/${serverId}/monitor/start`, {
      method: 'POST',
    });
  }

  async stopMonitoring(serverId) {
    return this.request(`/servers/${serverId}/monitor/stop`, {
      method: 'POST',
    });
  }

  async getServerMetrics(serverId) {
    return this.request(`/servers/${serverId}/metrics`);
  }

  // Alert management
  async getAlerts() {
    return this.request('/alerts/');
  }

  async getActiveAlerts() {
    return this.request('/alerts/active/');
  }

  async createAlert(alertData) {
    return this.request('/alerts/', {
      method: 'POST',
      body: JSON.stringify(alertData),
    });
  }

  async getAlertHistory(limit = 100) {
    return this.request(`/alerts/history/?limit=${limit}`);
  }

  async resolveAlert(alertId) {
    return this.request(`/alerts/${alertId}/resolve`, {
      method: 'POST',
    });
  }

  async acknowledgeAlert(alertId) {
    return this.request(`/alerts/${alertId}/acknowledge`, {
      method: 'POST',
    });
  }

  async deleteAlert(alertId) {
    return this.request(`/alerts/${alertId}`, {
      method: 'DELETE',
    });
  }

  // Real-time server status
  async getServerStatus(serverId) {
    return this.request(`/servers/${serverId}/status`);
  }

  async getAllServerStatuses() {
    return this.request('/servers/status/');
  }

  // Real-time metrics endpoints
  async getRealtimeMetrics(serverId) {
    return this.request(`/servers/${serverId}/metrics/realtime`);
  }

  async getMetricsHistory(serverId, timeRange = '1h') {
    return this.request(`/servers/${serverId}/metrics/history?range=${timeRange}`);
  }

  // WebSocket subscription management
  async getSubscriptionStatus() {
    return this.request('/ws/subscriptions/');
  }

  // System health and monitoring
  async getSystemHealth() {
    return this.request('/health/detailed');
  }

  async getMonitoringStatus() {
    return this.request('/monitoring/status/');
  }

  // Log management
  async getLogSources() {
    return this.request('/logs/sources/');
  }

  async createLogSource(logSourceData) {
    return this.request('/logs/sources/', {
      method: 'POST',
      body: JSON.stringify(logSourceData),
    });
  }

  async analyzeLogs(serverId) {
    return this.request(`/logs/analyze/${serverId}`);
  }

  async getRecentLogs(logSourceId, limit = 50) {
    return this.request(`/logs/recent/${logSourceId}?limit=${limit}`);
  }

  // Health check
  async healthCheck() {
    return this.request('/health');
  }
}

export default new ApiService();