import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import apiService from '../services/apiService';
import websocketService from '../utils/websocketService';

const AlertList = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => {
    fetchAlerts();
    initializeWebSocket();
    
    return () => {
      cleanupWebSocket();
    };
  }, []);

  const initializeWebSocket = async () => {
    try {
      await websocketService.connect();
      websocketService.subscribe('alerts');
      
      websocketService.onMessage('alert_created', handleAlertCreated);
      websocketService.onMessage('alert_resolved', handleAlertResolved);
      websocketService.onMessage('alert_updated', handleAlertUpdated);
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
    }
  };

  const cleanupWebSocket = () => {
    websocketService.offMessage('alert_created', handleAlertCreated);
    websocketService.offMessage('alert_resolved', handleAlertResolved);
    websocketService.offMessage('alert_updated', handleAlertUpdated);
  };

  const handleAlertCreated = (alert) => {
    setAlerts(prev => [alert, ...prev]);
  };

  const handleAlertResolved = (alert) => {
    setAlerts(prev => prev.map(a => 
      a.id === alert.id ? { ...a, status: 'resolved', resolved_at: alert.resolved_at } : a
    ));
  };

  const handleAlertUpdated = (alert) => {
    setAlerts(prev => prev.map(a => 
      a.id === alert.id ? { ...a, ...alert } : a
    ));
  };

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const alertsData = await apiService.getAlerts();
      setAlerts(alertsData);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const acknowledgeAlert = async (alertId) => {
    try {
      await apiService.acknowledgeAlert(alertId);
      setAlerts(prev => prev.map(alert => 
        alert.id === alertId 
          ? { ...alert, acknowledged: true, acknowledged_at: new Date().toISOString() }
          : alert
      ));
    } catch (error) {
      console.error('Error acknowledging alert:', error);
    }
  };

  const resolveAlert = async (alertId) => {
    try {
      await apiService.resolveAlert(alertId);
      setAlerts(prev => prev.map(alert => 
        alert.id === alertId 
          ? { ...alert, status: 'resolved', resolved_at: new Date().toISOString() }
          : alert
      ));
    } catch (error) {
      console.error('Error resolving alert:', error);
    }
  };

  const deleteAlert = async (alertId) => {
    if (window.confirm('Are you sure you want to delete this alert?')) {
      try {
        await apiService.deleteAlert(alertId);
        setAlerts(prev => prev.filter(alert => alert.id !== alertId));
      } catch (error) {
        console.error('Error deleting alert:', error);
      }
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'text-red-600 bg-red-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      case 'info':
        return 'text-blue-600 bg-blue-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'resolved':
        return 'text-green-600 bg-green-100';
      case 'acknowledged':
        return 'text-blue-600 bg-blue-100';
      case 'active':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const filteredAlerts = alerts.filter(alert => {
    if (filter === 'all') return true;
    if (filter === 'active') return alert.status === 'active';
    if (filter === 'acknowledged') return alert.acknowledged && alert.status !== 'resolved';
    if (filter === 'resolved') return alert.status === 'resolved';
    return true;
  });

  const sortedAlerts = [...filteredAlerts].sort((a, b) => {
    let aVal = a[sortBy];
    let bVal = b[sortBy];
    
    if (sortBy === 'created_at' || sortBy === 'acknowledged_at' || sortBy === 'resolved_at') {
      aVal = new Date(aVal);
      bVal = new Date(bVal);
    }
    
    if (sortOrder === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });

  if (loading) {
    return (
      <div className="content-area">
        <div className="flex justify-center items-center h-64">
          <div className="spinner"></div>
          <span className="ml-2">Loading alerts...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="content-area">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Alerts</h1>
          <p className="text-gray-600">Monitor and manage system alerts</p>
        </div>
        <Link to="/alerts/new" className="btn btn-primary">
          <i className="fas fa-plus mr-2"></i>
          Create Alert
        </Link>
      </div>

      {/* Filters and Controls */}
      <div className="card mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <select
              className="form-select"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="all">All Alerts</option>
              <option value="active">Active</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
          <div className="flex gap-2">
            <select
              className="form-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="created_at">Sort by Date</option>
              <option value="severity">Sort by Severity</option>
              <option value="status">Sort by Status</option>
            </select>
            <button
              className="btn btn-secondary"
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            >
              <i className={`fas ${sortOrder === 'asc' ? 'fa-arrow-up' : 'fa-arrow-down'}`}></i>
            </button>
          </div>
        </div>
      </div>

      {/* Alerts List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            Alert List ({sortedAlerts.length} of {alerts.length})
          </h3>
        </div>

        {sortedAlerts.length === 0 ? (
          <div className="text-center py-12">
            <i className="fas fa-bell text-6xl text-gray-300 mb-4"></i>
            <h3 className="text-xl font-semibold text-gray-600 mb-2">No alerts found</h3>
            <p className="text-gray-500 mb-6">
              {filter === 'all' 
                ? 'No alerts have been created yet' 
                : `No ${filter} alerts found`
              }
            </p>
            <Link to="/alerts/new" className="btn btn-primary">
              <i className="fas fa-plus mr-2"></i>
              Create Your First Alert
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Title</th>
                  <th>Server</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedAlerts.map((alert) => (
                  <tr key={alert.id}>
                    <td>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(alert.severity)}`}>
                        {alert.severity || 'Unknown'}
                      </span>
                    </td>
                    <td>
                      <div>
                        <div className="font-medium">{alert.title || 'Alert'}</div>
                        <div className="text-sm text-gray-600">{alert.message}</div>
                      </div>
                    </td>
                    <td className="text-gray-600">
                      {alert.server_name || 'N/A'}
                    </td>
                    <td>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(alert.status)}`}>
                        {alert.status || 'active'}
                        {alert.acknowledged && !alert.resolved_at && ' (Ack)'}
                      </span>
                    </td>
                    <td className="text-gray-600">
                      {new Date(alert.created_at).toLocaleString()}
                    </td>
                    <td>
                      <div className="flex space-x-2">
                        {!alert.acknowledged && (
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={() => acknowledgeAlert(alert.id)}
                            title="Acknowledge Alert"
                          >
                            <i className="fas fa-check"></i>
                          </button>
                        )}
                        {alert.status !== 'resolved' && (
                          <button
                            className="btn btn-sm btn-success"
                            onClick={() => resolveAlert(alert.id)}
                            title="Resolve Alert"
                          >
                            <i className="fas fa-check-double"></i>
                          </button>
                        )}
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => deleteAlert(alert.id)}
                          title="Delete Alert"
                        >
                          <i className="fas fa-trash"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-6">
        <div className="card text-center">
          <i className="fas fa-bell text-3xl text-blue-500 mb-2"></i>
          <div className="text-2xl font-bold text-gray-900">{alerts.length}</div>
          <div className="text-gray-600">Total Alerts</div>
        </div>
        <div className="card text-center">
          <i className="fas fa-exclamation-circle text-3xl text-red-500 mb-2"></i>
          <div className="text-2xl font-bold text-gray-900">
            {alerts.filter(a => a.status === 'active').length}
          </div>
          <div className="text-gray-600">Active</div>
        </div>
        <div className="card text-center">
          <i className="fas fa-check-circle text-3xl text-yellow-500 mb-2"></i>
          <div className="text-2xl font-bold text-gray-900">
            {alerts.filter(a => a.acknowledged && a.status !== 'resolved').length}
          </div>
          <div className="text-gray-600">Acknowledged</div>
        </div>
        <div className="card text-center">
          <i className="fas fa-check-double text-3xl text-green-500 mb-2"></i>
          <div className="text-2xl font-bold text-gray-900">
            {alerts.filter(a => a.status === 'resolved').length}
          </div>
          <div className="text-gray-600">Resolved</div>
        </div>
      </div>
    </div>
  );
};

export default AlertList;