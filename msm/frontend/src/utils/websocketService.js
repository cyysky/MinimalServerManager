// WebSocket Service for Minimal Server Manager
// Handles real-time communication between frontend and backend

class WebSocketService {
  constructor() {
    this.socket = null;
    this.reconnectInterval = 5000; // 5 seconds
    this.maxReconnectAttempts = 10;
    this.reconnectAttempts = 0;
    this.messageHandlers = {};
    this.isConnected = false;
    this.connectionPromise = null;
    this.connectionResolve = null;
    this.subscriptions = new Set();
    this.heartbeatInterval = null;
    this.lastPingTime = null;
    this.backendUrl = 'ws://localhost:8000/ws';
  }

  // Initialize WebSocket connection
  connect(backendUrl = null) {
    if (backendUrl) {
      this.backendUrl = backendUrl;
    }
    
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return Promise.resolve();
    }

    this.connectionPromise = new Promise((resolve) => {
      this.connectionResolve = resolve;
    });

    this.socket = new WebSocket(this.backendUrl);

    this.socket.onopen = () => {
      console.log('WebSocket connected successfully');
      this.isConnected = true;
      this.reconnectAttempts = 0;
      
      // Start heartbeat
      this.startHeartbeat();
      
      // Resubscribe to all previous subscriptions
      this.resubscribeAll();
      
      if (this.connectionResolve) {
        this.connectionResolve();
        this.connectionResolve = null;
      }
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log('WebSocket message received:', message);
        
        // Handle different message types
        this.handleMessage(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.socket.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      this.isConnected = false;
      this.stopHeartbeat();
      
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        setTimeout(() => this.connect(), this.reconnectInterval);
      } else {
        console.error('Max reconnection attempts reached');
        // Notify all handlers about connection failure
        this.handleMessage({ type: 'connection_failed', data: { attempts: this.reconnectAttempts } });
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return this.connectionPromise;
  }

  // Disconnect WebSocket
  disconnect() {
    this.stopHeartbeat();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.isConnected = false;
      this.reconnectAttempts = 0;
      this.subscriptions.clear();
    }
  }

  // Start heartbeat to keep connection alive
  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected) {
        this.ping();
      }
    }, 30000); // Ping every 30 seconds
  }

  // Stop heartbeat
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  // Subscribe to specific updates
  subscribe(subscriptionType, serverId = null) {
    const subscription = serverId ? `${subscriptionType}:${serverId}` : subscriptionType;
    this.subscriptions.add(subscription);
    
    if (this.isConnected) {
      this.sendMessage({
        type: 'subscribe',
        subscription: subscriptionType,
        server_id: serverId
      });
    }
    
    console.log(`Subscribed to: ${subscription}`);
  }

  // Unsubscribe from updates
  unsubscribe(subscriptionType, serverId = null) {
    const subscription = serverId ? `${subscriptionType}:${serverId}` : subscriptionType;
    this.subscriptions.delete(subscription);
    
    if (this.isConnected) {
      this.sendMessage({
        type: 'unsubscribe',
        subscription: subscriptionType,
        server_id: serverId
      });
    }
    
    console.log(`Unsubscribed from: ${subscription}`);
  }

  // Resubscribe to all previous subscriptions after reconnection
  resubscribeAll() {
    this.subscriptions.forEach(subscription => {
      const [type, serverId] = subscription.split(':');
      this.sendMessage({
        type: 'subscribe',
        subscription: type,
        server_id: serverId === type ? null : serverId
      });
    });
  }

  // Send message through WebSocket
  sendMessage(message) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected. Message not sent:', message);
      return false;
    }

    try {
      const jsonMessage = typeof message === 'string' ? message : JSON.stringify(message);
      this.socket.send(jsonMessage);
      console.log('WebSocket message sent:', message);
      return true;
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      return false;
    }
  }

  // Register message handler
  onMessage(type, handler) {
    if (!this.messageHandlers[type]) {
      this.messageHandlers[type] = [];
    }
    this.messageHandlers[type].push(handler);
  }

  // Remove message handler
  offMessage(type, handler) {
    if (this.messageHandlers[type]) {
      this.messageHandlers[type] = this.messageHandlers[type].filter(h => h !== handler);
    }
  }

  // Handle incoming messages
  handleMessage(message) {
    if (!message || !message.type) {
      console.warn('Invalid message format:', message);
      return;
    }

    console.log('WebSocket message received:', message);

    // Handle system messages
    switch (message.type) {
      case 'pong':
        console.log('Received pong from server');
        this.lastPingTime = Date.now();
        break;
      case 'subscribed':
        console.log('Successfully subscribed to:', message.subscription);
        break;
      case 'unsubscribed':
        console.log('Successfully unsubscribed from:', message.subscription);
        break;
      case 'error':
        console.error('Server error:', message.data);
        // Notify error handlers
        if (this.messageHandlers['error']) {
          this.messageHandlers['error'].forEach(handler => {
            try {
              handler(message);
            } catch (error) {
              console.error('Error in error handler:', error);
            }
          });
        }
        break;
      case 'connection_failed':
        console.error('WebSocket connection failed after', message.data.attempts, 'attempts');
        break;
    }

    // Handle real-time updates
    switch (message.type) {
      case 'server_status_update':
        this.handleServerStatusUpdate(message.data);
        break;
      case 'server_metrics_update':
        this.handleServerMetricsUpdate(message.data);
        break;
      case 'alert_created':
        this.handleAlertCreated(message.data);
        break;
      case 'alert_resolved':
        this.handleAlertResolved(message.data);
        break;
      case 'server_created':
      case 'server_updated':
      case 'server_deleted':
        this.handleServerChange(message);
        break;
    }

    // Handle custom message types
    if (this.messageHandlers[message.type]) {
      this.messageHandlers[message.type].forEach(handler => {
        try {
          handler(message);
        } catch (error) {
          console.error('Error in message handler:', error);
        }
      });
    }
  }

  // Handle server status updates
  handleServerStatusUpdate(data) {
    console.log('Server status update:', data);
    if (this.messageHandlers['server_status_update']) {
      this.messageHandlers['server_status_update'].forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error('Error in server status handler:', error);
        }
      });
    }
  }

  // Handle server metrics updates
  handleServerMetricsUpdate(data) {
    console.log('Server metrics update:', data);
    if (this.messageHandlers['server_metrics_update']) {
      this.messageHandlers['server_metrics_update'].forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error('Error in server metrics handler:', error);
        }
      });
    }
  }

  // Handle alert created
  handleAlertCreated(data) {
    console.log('New alert created:', data);
    if (this.messageHandlers['alert_created']) {
      this.messageHandlers['alert_created'].forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error('Error in alert created handler:', error);
        }
      });
    }
  }

  // Handle alert resolved
  handleAlertResolved(data) {
    console.log('Alert resolved:', data);
    if (this.messageHandlers['alert_resolved']) {
      this.messageHandlers['alert_resolved'].forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error('Error in alert resolved handler:', error);
        }
      });
    }
  }

  // Handle server changes (create, update, delete)
  handleServerChange(message) {
    console.log('Server change:', message.type, message.data);
    if (this.messageHandlers[message.type]) {
      this.messageHandlers[message.type].forEach(handler => {
        try {
          handler(message.data);
        } catch (error) {
          console.error('Error in server change handler:', error);
        }
      });
    }
  }

  // Send ping to check connection
  ping() {
    return this.sendMessage({ type: 'ping', timestamp: new Date().toISOString() });
  }

  // Get connection status
  getStatus() {
    return {
      isConnected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.maxReconnectAttempts
    };
  }
}

// Singleton instance
const websocketService = new WebSocketService();

export default websocketService;