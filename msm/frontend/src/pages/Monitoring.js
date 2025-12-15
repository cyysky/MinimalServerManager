import React, { useState, useEffect } from 'react';
import websocketService from '../utils/websocketService';

const Monitoring = () => {
  const [metrics, setMetrics] = useState({
    cpu: 0,
    memory: 0,
    disk: 0,
    network: 0,
    uptime: 0
  });
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [wsStatus, setWsStatus] = useState('disconnected');
  const isConnected = wsStatus === 'connected';

  useEffect(() => {
    // Load initial data
    loadMonitoringData();
    
    // Set up WebSocket connection
    initializeWebSocket();
    
    return () => {
      cleanupWebSocket();
    };
  }, []);

  const initializeWebSocket = async () => {
    try {
      setWsStatus('connecting');
      await websocketService.connect();
      setWsStatus('connected');
      
      // Subscribe to real-time updates
      websocketService.subscribe('server_status');
      websocketService.subscribe('server_metrics');
      websocketService.subscribe('alerts');
      websocketService.subscribe('status_update');
      websocketService.subscribe('metrics_update');
      websocketService.subscribe('monitoring_started');
      websocketService.subscribe('monitoring_stopped');
      
      // Set up message handlers for backend message types
      websocketService.onMessage('server_status_change', handleServerStatusUpdate);
      websocketService.onMessage('metrics_update', handleServerMetricsUpdate);
      websocketService.onMessage('server_statuses', handleServerStatuses);
      websocketService.onMessage('monitoring_started', handleMonitoringStarted);
      websocketService.onMessage('monitoring_stopped', handleMonitoringStopped);
      websocketService.onMessage('alert_created', handleAlertCreated);
      websocketService.onMessage('alert_resolved', handleAlertResolved);
      websocketService.onMessage('connection_failed', handleConnectionFailed);
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      setWsStatus('error');
    }
  };

  const cleanupWebSocket = () => {
    websocketService.offMessage('server_status_change', handleServerStatusUpdate);
    websocketService.offMessage('server_statuses', handleServerStatuses);
    websocketService.offMessage('metrics_update', handleServerMetricsUpdate);
    websocketService.offMessage('monitoring_started', handleMonitoringStarted);
    websocketService.offMessage('monitoring_stopped', handleMonitoringStopped);
    websocketService.offMessage('alert_created', handleAlertCreated);
    websocketService.offMessage('alert_resolved', handleAlertResolved);
    websocketService.offMessage('connection_failed', handleConnectionFailed);
  };

  const handleServerStatusUpdate = (data) => {
    console.log('Server status update:', data);
    // Update server status in the list
    setServers(prevServers =>
      prevServers.map(server =>
        server.id === data.server_id
          ? { ...server, status: data.status, last_seen: data.timestamp }
          : server
      )
    );
  };

  const handleServerStatuses = (data) => {
    console.log('Server statuses update:', data);
    // Update all server statuses
    if (data.data) {
      const serverStatuses = data.data;
      setServers(prevServers =>
        prevServers.map(server => ({
          ...server,
          status: serverStatuses[server.id] || 'offline'
        }))
      );
    }
  };

  const handleServerMetricsUpdate = (data) => {
    console.log('Server metrics update:', data);
    // Update server metrics in the list
    if (data.data && data.data.metrics) {
      const metrics = data.data.metrics;
      setServers(prevServers =>
        prevServers.map(server =>
          server.id === data.data.server_id
            ? {
                ...server,
                cpu: Math.round(metrics.cpu_usage?.totalUsage || 0),
                memory: Math.round(metrics.memory_usage?.usage_percent || 0),
                disk: Math.round(metrics.disk_usage?.[0]?.usage_percent || 0)
              }
            : server
        )
      );
    }
  };

  const handleMonitoringStarted = (data) => {
    console.log('Monitoring started:', data);
    // Reload data when monitoring starts
    loadMonitoringData();
  };

  const handleMonitoringStopped = (data) => {
    console.log('Monitoring stopped:', data);
    // Reload data when monitoring stops
    loadMonitoringData();
  };

  const handleAlertCreated = (data) => {
    console.log('New alert:', data);
    // Handle new alerts if needed
  };

  const handleAlertResolved = (data) => {
    console.log('Alert resolved:', data);
    // Handle resolved alerts if needed
  };

  const handleConnectionFailed = (data) => {
    console.error('WebSocket connection failed:', data);
    setWsStatus('error');
  };

  const loadMonitoringData = async () => {
    try {
      setLoading(true);
      
      // Load servers list
      const serversResponse = await fetch('http://localhost:8000/servers/');
      let allServers = [];
      if (serversResponse.ok) {
        allServers = await serversResponse.json();
        setServers(allServers || []);
      }
      
      // Load real-time status
      const statusResponse = await fetch('http://localhost:8000/status/realtime');
      if (statusResponse.ok) {
        const statusData = await statusResponse.json();
        const serverStatuses = statusData.server_statuses || {};
        
        // Update servers with status information
        setServers(prevServers =>
          prevServers.map(server => ({
            ...server,
            status: serverStatuses[server.id] || 'offline'
          }))
        );
      }
      
      // Calculate overall metrics from all servers
      if (allServers.length > 0) {
        // Get metrics for each server
        const metricsPromises = allServers.map(async (server) => {
          try {
            const metricsResponse = await fetch(`http://localhost:8000/servers/${server.id}/metrics`);
            if (metricsResponse.ok) {
              const metrics = await metricsResponse.json();
              return { server, metrics };
            }
          } catch (error) {
            console.warn(`Failed to get metrics for server ${server.id}:`, error);
          }
          return null;
        });
        
        const metricsResults = await Promise.all(metricsPromises);
        const validMetrics = metricsResults.filter(m => m !== null);
        
        if (validMetrics.length > 0) {
          // Calculate average metrics from all servers
          const avgCpu = validMetrics.reduce((sum, m) => sum + (m.metrics.cpu_usage?.totalUsage || 0), 0) / validMetrics.length;
          const avgMemory = validMetrics.reduce((sum, m) => sum + (m.metrics.memory_usage?.usage_percent || 0), 0) / validMetrics.length;
          const avgDisk = validMetrics.reduce((sum, m) => sum + (m.metrics.disk_usage?.[0]?.usage_percent || 0), 0) / validMetrics.length;
          
          setMetrics({
            cpu: Math.round(avgCpu),
            memory: Math.round(avgMemory),
            disk: Math.round(avgDisk),
            network: 0, // Network data not available in current metrics
            uptime: 0 // Uptime data not available in current metrics
          });
          
          // Update individual server data with metrics
          setServers(prevServers =>
            prevServers.map(server => {
              const serverMetrics = validMetrics.find(m => m.server.id === server.id);
              if (serverMetrics) {
                return {
                  ...server,
                  cpu: Math.round(serverMetrics.metrics.cpu_usage?.totalUsage || 0),
                  memory: Math.round(serverMetrics.metrics.memory_usage?.usage_percent || 0),
                  disk: Math.round(serverMetrics.metrics.disk_usage?.[0]?.usage_percent || 0)
                };
              }
              return server;
            })
          );
        }
      }
      
    } catch (error) {
      console.error('Failed to load monitoring data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatUptime = (seconds) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  };

  const getStatusColor = (value, thresholds) => {
    if (value >= thresholds.critical) return 'text-red-600';
    if (value >= thresholds.warning) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getProgressBarColor = (value, thresholds) => {
    if (value >= thresholds.critical) return 'bg-red-500';
    if (value >= thresholds.warning) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const cpuThresholds = { warning: 70, critical: 90 };
  const memoryThresholds = { warning: 80, critical: 95 };
  const diskThresholds = { warning: 85, critical: 95 };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">System Monitoring</h1>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className="text-sm text-gray-600">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* System Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* CPU Usage */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">CPU Usage</p>
              <p className={`text-2xl font-bold ${getStatusColor(metrics.cpu, cpuThresholds)}`}>
                {metrics.cpu}%
              </p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <i className="fas fa-microchip text-blue-600"></i>
            </div>
          </div>
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full ${getProgressBarColor(metrics.cpu, cpuThresholds)}`}
                style={{ width: `${metrics.cpu}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Memory Usage */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Memory Usage</p>
              <p className={`text-2xl font-bold ${getStatusColor(metrics.memory, memoryThresholds)}`}>
                {metrics.memory}%
              </p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <i className="fas fa-memory text-green-600"></i>
            </div>
          </div>
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full ${getProgressBarColor(metrics.memory, memoryThresholds)}`}
                style={{ width: `${metrics.memory}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Disk Usage */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Disk Usage</p>
              <p className={`text-2xl font-bold ${getStatusColor(metrics.disk, diskThresholds)}`}>
                {metrics.disk}%
              </p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
              <i className="fas fa-hdd text-purple-600"></i>
            </div>
          </div>
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full ${getProgressBarColor(metrics.disk, diskThresholds)}`}
                style={{ width: `${metrics.disk}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Network Traffic */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Network</p>
              <p className="text-2xl font-bold text-blue-600">
                {metrics.network} MB/s
              </p>
            </div>
            <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
              <i className="fas fa-network-wired text-orange-600"></i>
            </div>
          </div>
          <div className="mt-4">
            <p className="text-xs text-gray-500">
              Uptime: {formatUptime(metrics.uptime)}
            </p>
          </div>
        </div>
      </div>

      {/* Server Status Table */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Server Status</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Server
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  CPU
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Memory
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Disk
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Uptime
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {servers.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-4 text-center text-gray-500">
                    No servers configured. <a href="/servers/new" className="text-blue-600 hover:underline">Add a server</a> to start monitoring.
                  </td>
                </tr>
              ) : (
                servers.map((server) => (
                  <tr key={server.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-8 w-8">
                          <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
                            server.status === 'online' ? 'bg-green-100' : 'bg-red-100'
                          }`}>
                            <i className={`fas fa-server ${
                              server.status === 'online' ? 'text-green-600' : 'text-red-600'
                            }`}></i>
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{server.name}</div>
                          <div className="text-sm text-gray-500">{server.ip}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        server.status === 'online' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {server.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className={getStatusColor(server.cpu || 0, cpuThresholds)}>
                        {server.cpu || 0}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className={getStatusColor(server.memory || 0, memoryThresholds)}>
                        {server.memory || 0}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className={getStatusColor(server.disk || 0, diskThresholds)}>
                        {server.disk || 0}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {server.uptime ? formatUptime(server.uptime) : 'N/A'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Real-time Charts Placeholder */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">CPU Usage Over Time</h3>
          <div className="h-64 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <i className="fas fa-chart-line text-4xl mb-2"></i>
              <p>Real-time chart will be displayed here</p>
              <p className="text-sm">Chart library integration needed</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Memory Usage Over Time</h3>
          <div className="h-64 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <i className="fas fa-chart-area text-4xl mb-2"></i>
              <p>Real-time chart will be displayed here</p>
              <p className="text-sm">Chart library integration needed</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Monitoring;