import React, { useState, useEffect } from 'react';
import AlertNotification from './AlertNotification';
import websocketService from '../utils/websocketService';

const AlertManager = () => {
  const [alerts, setAlerts] = useState([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    initializeAlertManager();
    
    return () => {
      cleanupAlertManager();
    };
  }, []);

  const initializeAlertManager = async () => {
    try {
      // Connect to WebSocket if not already connected
      if (!websocketService.getStatus().isConnected) {
        await websocketService.connect();
      }
      setIsConnected(true);
      
      // Subscribe to alert notifications
      websocketService.subscribe('alerts');
      
      // Set up alert message handlers
      websocketService.onMessage('alert_created', handleNewAlert);
      websocketService.onMessage('alert_resolved', handleAlertResolved);
      websocketService.onMessage('alert_updated', handleAlertUpdated);
      
      console.log('AlertManager initialized');
    } catch (error) {
      console.error('Failed to initialize AlertManager:', error);
      setIsConnected(false);
    }
  };

  const cleanupAlertManager = () => {
    websocketService.offMessage('alert_created', handleNewAlert);
    websocketService.offMessage('alert_resolved', handleAlertResolved);
    websocketService.offMessage('alert_updated', handleAlertUpdated);
  };

  const handleNewAlert = (alertData) => {
    console.log('New alert received:', alertData);
    
    // Add the new alert to our list
    const newAlert = {
      id: alertData.id || Date.now(),
      title: alertData.title || 'Server Alert',
      message: alertData.message || 'A new alert has been triggered',
      severity: alertData.severity || 'info',
      server_name: alertData.server_name,
      server_id: alertData.server_id,
      created_at: alertData.created_at || new Date().toISOString(),
      acknowledged: false,
      status: 'active'
    };
    
    setAlerts(prev => [newAlert, ...prev].slice(0, 10)); // Keep only latest 10 alerts
    
    // Show browser notification if permission granted
    if (Notification.permission === 'granted') {
      new Notification(`Alert: ${newAlert.title}`, {
        body: newAlert.message,
        icon: '/favicon.ico',
        tag: newAlert.id
      });
    }
  };

  const handleAlertResolved = (alertData) => {
    console.log('Alert resolved:', alertData);
    setAlerts(prev => prev.map(alert => 
      alert.id === alertData.id 
        ? { ...alert, status: 'resolved', resolved_at: alertData.resolved_at }
        : alert
    ));
  };

  const handleAlertUpdated = (alertData) => {
    console.log('Alert updated:', alertData);
    setAlerts(prev => prev.map(alert => 
      alert.id === alertData.id 
        ? { ...alert, ...alertData }
        : alert
    ));
  };

  const handleAcknowledgeAlert = (alert) => {
    console.log('Alert acknowledged:', alert);
    setAlerts(prev => prev.map(a => 
      a.id === alert.id 
        ? { ...a, acknowledged: true, acknowledged_at: new Date().toISOString() }
        : a
    ));
  };

  const handleDismissAlert = (alert) => {
    console.log('Alert dismissed:', alert);
    setAlerts(prev => prev.filter(a => a.id !== alert.id));
  };

  const requestNotificationPermission = () => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          console.log('Notification permission granted');
        }
      });
    }
  };

  // Request notification permission on mount
  useEffect(() => {
    requestNotificationPermission();
  }, []);

  // Auto-remove resolved alerts after 30 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setAlerts(prev => prev.filter(alert => {
        if (alert.status === 'resolved') {
          const resolvedTime = new Date(alert.resolved_at || alert.updated_at);
          const now = new Date();
          return (now - resolvedTime) < 30000; // 30 seconds
        }
        return true;
      }));
    }, 5000); // Check every 5 seconds

    return () => clearInterval(timer);
  }, []);

  return (
    <>
      {/* Alert Notifications */}
      {alerts.map((alert) => (
        <AlertNotification
          key={alert.id}
          alert={alert}
          onAcknowledge={handleAcknowledgeAlert}
          onDismiss={handleDismissAlert}
        />
      ))}
      
      {/* Connection Status Indicator (Development) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 left-4 z-50">
          <div className={`px-3 py-1 rounded-full text-xs font-medium ${
            isConnected 
              ? 'bg-green-100 text-green-800' 
              : 'bg-red-100 text-red-800'
          }`}>
            <i className={`fas ${isConnected ? 'fa-wifi' : 'fa-wifi-slash'} mr-1`}></i>
            Alert Manager {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      )}
    </>
  );
};

export default AlertManager;