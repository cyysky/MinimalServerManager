import React, { useState, useEffect } from 'react';
import apiService from '../services/apiService';
import websocketService from '../utils/websocketService';

const AlertNotification = ({ alert, onAcknowledge, onDismiss }) => {
  const [isVisible, setIsVisible] = useState(true);
  const [isAcknowledging, setIsAcknowledging] = useState(false);

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'bg-red-100 border-red-500 text-red-800';
      case 'warning':
        return 'bg-yellow-100 border-yellow-500 text-yellow-800';
      case 'info':
        return 'bg-blue-100 border-blue-500 text-blue-800';
      default:
        return 'bg-gray-100 border-gray-500 text-gray-800';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'fas fa-exclamation-triangle';
      case 'warning':
        return 'fas fa-exclamation-circle';
      case 'info':
        return 'fas fa-info-circle';
      default:
        return 'fas fa-bell';
    }
  };

  const handleAcknowledge = async () => {
    try {
      setIsAcknowledging(true);
      await apiService.acknowledgeAlert(alert.id);
      onAcknowledge?.(alert);
      setIsVisible(false);
    } catch (error) {
      console.error('Error acknowledging alert:', error);
    } finally {
      setIsAcknowledging(false);
    }
  };

  const handleDismiss = () => {
    setIsVisible(false);
    onDismiss?.(alert);
  };

  if (!isVisible) return null;

  return (
    <div className={`fixed top-4 right-4 max-w-md p-4 border-l-4 rounded-lg shadow-lg z-50 ${getSeverityColor(alert.severity)}`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <i className={`${getSeverityIcon(alert.severity)} text-lg`}></i>
        </div>
        <div className="ml-3 flex-1">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">
              {alert.title || 'Server Alert'}
            </h3>
            <button
              onClick={handleDismiss}
              className="ml-2 text-gray-400 hover:text-gray-600"
            >
              <i className="fas fa-times"></i>
            </button>
          </div>
          <div className="mt-1 text-sm">
            <p>{alert.message}</p>
            {alert.server_name && (
              <p className="mt-1 text-xs opacity-75">
                Server: {alert.server_name}
              </p>
            )}
            {alert.created_at && (
              <p className="mt-1 text-xs opacity-75">
                {new Date(alert.created_at).toLocaleString()}
              </p>
            )}
          </div>
          <div className="mt-3 flex space-x-2">
            <button
              onClick={handleAcknowledge}
              disabled={isAcknowledging}
              className="text-xs bg-white bg-opacity-50 hover:bg-opacity-75 px-3 py-1 rounded border"
            >
              {isAcknowledging ? (
                <div className="spinner mr-1"></div>
              ) : (
                <i className="fas fa-check mr-1"></i>
              )}
              Acknowledge
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AlertNotification;