import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import apiService from '../services/apiService';
import websocketService from '../utils/websocketService';

const ServerDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [server, setServer] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [realtimeMetrics, setRealtimeMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [wsStatus, setWsStatus] = useState('disconnected');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isMonitoring, setIsMonitoring] = useState(false);

  useEffect(() => {
    if (id) {
      fetchServerDetails();
      initializeWebSocket();
    }
    
    return () => {
      cleanupWebSocket();
    };
  }, [id]);

  const initializeWebSocket = async () => {
    try {
      setWsStatus('connecting');
      await websocketService.connect();
      setWsStatus('connected');
      
      // Subscribe to this specific server's updates
      websocketService.subscribe('server_status', id);
      websocketService.subscribe('server_metrics', id);
      
      // Set up message handlers
      websocketService.onMessage('server_status_update', handleServerStatusUpdate);
      websocketService.onMessage('server_metrics_update', handleServerMetricsUpdate);
      websocketService.onMessage('connection_failed', handleConnectionFailed);
      
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      setWsStatus('error');
    }
  };

  const cleanupWebSocket = () => {
    websocketService.offMessage('server_status_update', handleServerStatusUpdate);
    websocketService.offMessage('server_metrics_update', handleServerMetricsUpdate);
    websocketService.offMessage('connection_failed', handleConnectionFailed);
    // Unsubscribe from server-specific updates
    websocketService.unsubscribe('server_status', id);
    websocketService.unsubscribe('server_metrics', id);
  };

  const handleServerStatusUpdate = (data) => {
    console.log('Server status updated:', data);
    if (data.server_id === parseInt(id)) {
      setServer(prev => prev ? { ...prev, status: data.status, updated_at: data.timestamp } : null);
      setLastUpdate(new Date());
    }
  };

  const handleServerMetricsUpdate = (data) => {
    console.log('Server metrics updated:', data);
    if (data.server_id === parseInt(id)) {
      setRealtimeMetrics(data.metrics);
      setLastUpdate(new Date());
    }
  };

  const handleConnectionFailed = () => {
    setWsStatus('error');
  };

  const fetchServerDetails = async () => {
    try {
      setLoading(true);
      const serverData = await apiService.getServer(id);
      setServer(serverData);
      setIsMonitoring(serverData.monitoring_enabled || false);
    } catch (error) {
      console.error('Error fetching server details:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMetrics = async () => {
    try {
      setMetricsLoading(true);
      const metricsData = await apiService.getServerMetrics(id);
      setMetrics(metricsData);
    } catch (error) {
      console.error('Error fetching metrics:', error);
      setMetrics(null);
    } finally {
      setMetricsLoading(false);
    }
  };

  const toggleServerStatus = async () => {
    try {
      await apiService.toggleServerStatus(id);
      fetchServerDetails();
    } catch (error) {
      console.error('Error toggling server status:', error);
    }
  };

  const deleteServer = async () => {
    if (window.confirm('Are you sure you want to delete this server?')) {
      try {
        await apiService.deleteServer(id);
        navigate('/servers');
      } catch (error) {
        console.error('Error deleting server:', error);
      }
    }
  };

  const startMonitoring = async () => {
    try {
      await apiService.startMonitoring(id);
      setIsMonitoring(true);
      alert('Monitoring started successfully');
      // Subscribe to real-time metrics
      websocketService.subscribe('server_metrics', id);
    } catch (error) {
      console.error('Error starting monitoring:', error);
      alert('Failed to start monitoring: ' + error.message);
    }
  };

  const stopMonitoring = async () => {
    try {
      await apiService.stopMonitoring(id);
      setIsMonitoring(false);
      setRealtimeMetrics(null);
      alert('Monitoring stopped successfully');
      // Unsubscribe from real-time metrics
      websocketService.unsubscribe('server_metrics', id);
    } catch (error) {
      console.error('Error stopping monitoring:', error);
      alert('Failed to stop monitoring: ' + error.message);
    }
  };

  const fetchRealtimeMetrics = async () => {
    try {
      setMetricsLoading(true);
      const metricsData = await apiService.getRealtimeMetrics(id);
      setRealtimeMetrics(metricsData);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error fetching realtime metrics:', error);
    } finally {
      setMetricsLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="content-area">
        <div className="flex justify-center items-center h-64">
          <div className="spinner"></div>
          <span className="ml-2">Loading server details...</span>
        </div>
      </div>
    );
  }

  if (!server) {
    return (
      <div className="content-area">
        <div className="text-center py-12">
          <i className="fas fa-exclamation-triangle text-4xl text-yellow-500 mb-4"></i>
          <h3 className="text-xl font-semibold text-gray-600 mb-2">Server not found</h3>
          <p className="text-gray-500 mb-6">The server you're looking for doesn't exist</p>
          <Link to="/servers" className="btn btn-primary">
            Back to Servers
          </Link>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: 'fas fa-info-circle' },
    { id: 'metrics', label: 'Metrics', icon: 'fas fa-chart-line' },
    { id: 'monitoring', label: 'Monitoring', icon: 'fas fa-eye' },
    { id: 'logs', label: 'Logs', icon: 'fas fa-file-alt' },
  ];

  return (
    <div className="content-area">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center space-x-4">
          <Link to="/servers" className="btn btn-secondary btn-sm">
            <i className="fas fa-arrow-left mr-2"></i>
            Back
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{server.name}</h1>
            <p className="text-gray-600">{server.ip}:{server.port}</p>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          {/* WebSocket Status Indicator */}
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${
              wsStatus === 'connected' ? 'bg-green-500' :
              wsStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' :
              wsStatus === 'error' ? 'bg-red-500' : 'bg-gray-400'
            }`}></div>
            <span className="text-sm text-gray-600 capitalize">{wsStatus}</span>
          </div>
          {/* Last Update Time */}
          {lastUpdate && (
            <div className="text-sm text-gray-500">
              Updated: {lastUpdate.toLocaleTimeString()}
            </div>
          )}
          {/* Monitoring Status */}
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${
              isMonitoring ? 'bg-green-500' : 'bg-gray-400'
            }`}></div>
            <span className="text-sm text-gray-600">
              {isMonitoring ? 'Monitoring' : 'Not Monitoring'}
            </span>
          </div>
          <button
            className={`btn ${server.status === 'active' ? 'btn-warning' : 'btn-success'}`}
            onClick={toggleServerStatus}
          >
            <i className={`fas ${server.status === 'active' ? 'fa-pause' : 'fa-play'} mr-2`}></i>
            {server.status === 'active' ? 'Deactivate' : 'Activate'}
          </button>
          <button className="btn btn-danger" onClick={deleteServer}>
            <i className="fas fa-trash mr-2"></i>
            Delete
          </button>
        </div>
      </div>

      {/* Status Card */}
      <div className="card mb-6">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <div className={`w-4 h-4 rounded-full ${
              server.status === 'active' ? 'bg-green-500' : 'bg-red-500'
            }`}></div>
            <div>
              <h3 className="text-lg font-semibold">Server Status</h3>
              <p className="text-gray-600">
                Last updated: {new Date(server.updated_at).toLocaleString()}
              </p>
            </div>
          </div>
          <div className="text-right">
            <span className={`status-badge ${
              server.status === 'active' ? 'status-online' : 'status-offline'
            } text-lg px-4 py-2`}>
              {server.status}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="card mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab(tab.id)}
              >
                <i className={`${tab.icon} mr-2`}></i>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-lg font-semibold mb-4">Server Information</h4>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Name:</span>
                    <span className="font-medium">{server.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">IP Address:</span>
                    <span className="font-mono">{server.ip}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Port:</span>
                    <span className="font-medium">{server.port}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">User:</span>
                    <span className="font-medium">{server.user}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Status:</span>
                    <span className={`status-badge ${
                      server.status === 'active' ? 'status-online' : 'status-offline'
                    }`}>
                      {server.status}
                    </span>
                  </div>
                </div>
              </div>
              <div>
                <h4 className="text-lg font-semibold mb-4">Timestamps</h4>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Created:</span>
                    <span className="font-medium">{new Date(server.created_at).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Last Updated:</span>
                    <span className="font-medium">{new Date(server.updated_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Metrics Tab */}
          {activeTab === 'metrics' && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h4 className="text-lg font-semibold">Performance Metrics</h4>
                <div className="flex space-x-2">
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={fetchRealtimeMetrics}
                    disabled={metricsLoading || !isMonitoring}
                    title={!isMonitoring ? 'Start monitoring to enable real-time metrics' : 'Fetch latest metrics'}
                  >
                    {metricsLoading ? (
                      <div className="spinner mr-2"></div>
                    ) : (
                      <i className="fas fa-bolt mr-2"></i>
                    )}
                    Real-time
                  </button>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={fetchMetrics}
                    disabled={metricsLoading}
                  >
                    {metricsLoading ? (
                      <div className="spinner mr-2"></div>
                    ) : (
                      <i className="fas fa-sync-alt mr-2"></i>
                    )}
                    Refresh
                  </button>
                </div>
              </div>

              {/* Real-time Metrics Section */}
              {isMonitoring && realtimeMetrics && (
                <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <h5 className="font-semibold text-green-800">
                      <i className="fas fa-circle text-green-500 mr-2"></i>
                      Live Metrics
                    </h5>
                    <span className="text-sm text-green-600">
                      Last update: {lastUpdate?.toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Live CPU */}
                    {realtimeMetrics.cpu_usage && (
                      <div className="bg-white p-3 rounded border">
                        <div className="text-sm text-gray-600">CPU Usage</div>
                        <div className="text-xl font-bold text-blue-600">
                          {realtimeMetrics.cpu_usage.totalUsage?.toFixed(1)}%
                        </div>
                        <div className="text-xs text-gray-500">
                          User: {realtimeMetrics.cpu_usage.user?.toFixed(1)}% |
                          System: {realtimeMetrics.cpu_usage.system?.toFixed(1)}%
                        </div>
                      </div>
                    )}

                    {/* Live Memory */}
                    {realtimeMetrics.memory_usage && (
                      <div className="bg-white p-3 rounded border">
                        <div className="text-sm text-gray-600">Memory Usage</div>
                        <div className="text-xl font-bold text-green-600">
                          {realtimeMetrics.memory_usage.usage_percent?.toFixed(1)}%
                        </div>
                        <div className="text-xs text-gray-500">
                          {realtimeMetrics.memory_usage.used_mb}MB / {realtimeMetrics.memory_usage.total_mb}MB
                        </div>
                      </div>
                    )}

                    {/* Live Network */}
                    {realtimeMetrics.network && (
                      <div className="bg-white p-3 rounded border">
                        <div className="text-sm text-gray-600">Network I/O</div>
                        <div className="text-sm">
                          <div>In: {(realtimeMetrics.network.bytes_recv / 1024 / 1024).toFixed(1)} MB</div>
                          <div>Out: {(realtimeMetrics.network.bytes_sent / 1024 / 1024).toFixed(1)} MB</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Historical Metrics Section */}
              {!metrics && !metricsLoading && !realtimeMetrics && (
                <div className="text-center py-8">
                  <i className="fas fa-chart-line text-4xl text-gray-300 mb-4"></i>
                  <p className="text-gray-500 mb-4">
                    {!isMonitoring
                      ? 'Start monitoring to see real-time metrics'
                      : 'Click "Refresh" to load historical performance data'
                    }
                  </p>
                </div>
              )}

              {metrics && (
                <div>
                  <h5 className="font-semibold mb-4">Historical Metrics</h5>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* CPU Usage */}
                    {metrics.cpu_usage && (
                      <div className="card">
                        <h6 className="font-semibold mb-2">CPU Usage</h6>
                        <div className="text-2xl font-bold text-blue-600">
                          {metrics.cpu_usage.totalUsage?.toFixed(1)}%
                        </div>
                        <div className="text-sm text-gray-600 mt-2">
                          User: {metrics.cpu_usage.user?.toFixed(1)}% |
                          System: {metrics.cpu_usage.system?.toFixed(1)}%
                        </div>
                      </div>
                    )}

                    {/* Memory Usage */}
                    {metrics.memory_usage && (
                      <div className="card">
                        <h6 className="font-semibold mb-2">Memory Usage</h6>
                        <div className="text-2xl font-bold text-green-600">
                          {metrics.memory_usage.usage_percent?.toFixed(1)}%
                        </div>
                        <div className="text-sm text-gray-600 mt-2">
                          {metrics.memory_usage.used_mb}MB / {metrics.memory_usage.total_mb}MB
                        </div>
                      </div>
                    )}

                    {/* Disk Usage */}
                    {metrics.disk_usage && (
                      <div className="card">
                        <h6 className="font-semibold mb-2">Disk Usage</h6>
                        <div className="space-y-2">
                          {metrics.disk_usage.slice(0, 3).map((disk, index) => (
                            <div key={index} className="flex justify-between text-sm">
                              <span className="text-gray-600">{disk.mount_point}</span>
                              <span className="font-medium">{disk.usage_percent?.toFixed(1)}%</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Monitoring Tab */}
          {activeTab === 'monitoring' && (
            <div>
              <h4 className="text-lg font-semibold mb-4">Monitoring Control</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="card">
                  <h5 className="font-semibold mb-2">Start Monitoring</h5>
                  <p className="text-gray-600 mb-4">
                    Begin collecting real-time metrics and performance data for this server.
                  </p>
                  <button className="btn btn-success" onClick={startMonitoring}>
                    <i className="fas fa-play mr-2"></i>
                    Start Monitoring
                  </button>
                </div>
                <div className="card">
                  <h5 className="font-semibold mb-2">Stop Monitoring</h5>
                  <p className="text-gray-600 mb-4">
                    Stop collecting metrics for this server. Existing data will be preserved.
                  </p>
                  <button className="btn btn-warning" onClick={stopMonitoring}>
                    <i className="fas fa-stop mr-2"></i>
                    Stop Monitoring
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Logs Tab */}
          {activeTab === 'logs' && (
            <div>
              <h4 className="text-lg font-semibold mb-4">Server Logs</h4>
              <div className="text-center py-8">
                <i className="fas fa-file-alt text-4xl text-gray-300 mb-4"></i>
                <p className="text-gray-500">Log viewing functionality will be implemented in the next phase</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ServerDetail;