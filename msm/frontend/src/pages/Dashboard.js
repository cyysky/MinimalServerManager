import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import apiService from '../services/apiService';
import websocketService from '../utils/websocketService';

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalServers: 0,
    onlineServers: 0,
    offlineServers: 0,
    activeAlerts: 0
  });
  const [recentServers, setRecentServers] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [wsStatus, setWsStatus] = useState('disconnected');
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    fetchDashboardData();
    
    // Connect to WebSocket for real-time updates
    initializeWebSocket();
    
    // Set up periodic refresh as fallback
    const refreshInterval = setInterval(() => {
      fetchDashboardData();
    }, 30000); // Refresh every 30 seconds

    return () => {
      clearInterval(refreshInterval);
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
      
      // Set up message handlers
      websocketService.onMessage('server_status_update', handleServerStatusUpdate);
      websocketService.onMessage('server_metrics_update', handleServerMetricsUpdate);
      websocketService.onMessage('alert_created', handleAlertCreated);
      websocketService.onMessage('alert_resolved', handleAlertResolved);
      websocketService.onMessage('server_created', handleServerUpdate);
      websocketService.onMessage('server_updated', handleServerUpdate);
      websocketService.onMessage('server_deleted', handleServerUpdate);
      websocketService.onMessage('connection_failed', handleConnectionFailed);
      
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      setWsStatus('error');
    }
  };

  const cleanupWebSocket = () => {
    websocketService.offMessage('server_status_update', handleServerStatusUpdate);
    websocketService.offMessage('server_metrics_update', handleServerMetricsUpdate);
    websocketService.offMessage('alert_created', handleAlertCreated);
    websocketService.offMessage('alert_resolved', handleAlertResolved);
    websocketService.offMessage('server_created', handleServerUpdate);
    websocketService.offMessage('server_updated', handleServerUpdate);
    websocketService.offMessage('server_deleted', handleServerUpdate);
    websocketService.offMessage('connection_failed', handleConnectionFailed);
  };

  const handleServerStatusUpdate = (data) => {
    console.log('Server status updated:', data);
    setLastUpdate(new Date());
    // Update stats without full refresh
    updateServerStatusInStats(data);
  };

  const handleServerMetricsUpdate = (data) => {
    console.log('Server metrics updated:', data);
    setLastUpdate(new Date());
  };

  const handleAlertCreated = (alert) => {
    console.log('New alert:', alert);
    setAlerts(prev => [alert, ...prev].slice(0, 5)); // Keep only latest 5
    setStats(prev => ({ ...prev, activeAlerts: prev.activeAlerts + 1 }));
    setLastUpdate(new Date());
  };

  const handleAlertResolved = (alert) => {
    console.log('Alert resolved:', alert);
    setAlerts(prev => prev.filter(a => a.id !== alert.id));
    setStats(prev => ({ ...prev, activeAlerts: Math.max(0, prev.activeAlerts - 1) }));
    setLastUpdate(new Date());
  };

  const handleConnectionFailed = () => {
    setWsStatus('error');
  };

  const updateServerStatusInStats = (serverData) => {
    setStats(prev => {
      const newStats = { ...prev };
      if (serverData.status === 'active') {
        newStats.onlineServers += 1;
        newStats.offlineServers = Math.max(0, newStats.offlineServers - 1);
      } else {
        newStats.offlineServers += 1;
        newStats.onlineServers = Math.max(0, newStats.onlineServers - 1);
      }
      return newStats;
    });
  };

  const handleServerUpdate = () => {
    fetchDashboardData();
  };

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // Fetch servers and alerts in parallel
      const [servers, activeAlerts] = await Promise.all([
        apiService.getServers(),
        apiService.getActiveAlerts().catch(() => []) // Fallback if endpoint doesn't exist
      ]);
      
      // Calculate stats
      const onlineCount = servers.filter(server => server.status === 'active').length;
      const offlineCount = servers.filter(server => server.status === 'inactive').length;
      
      setStats({
        totalServers: servers.length,
        onlineServers: onlineCount,
        offlineServers: offlineCount,
        activeAlerts: activeAlerts.length || 0
      });
      
      // Set recent servers (last 5)
      setRecentServers(servers.slice(-5).reverse());
      
      // Set recent alerts
      setAlerts(activeAlerts.slice(0, 5));
      
      setLastUpdate(new Date());
      
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      // Don't show loading state on error for better UX
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ title, value, icon, color, link }) => (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">{title}</h3>
        <i className={`${icon} text-2xl ${color}`}></i>
      </div>
      <div className="text-center">
        <div className="text-3xl font-bold text-gray-900 mb-2">{value}</div>
        {link && (
          <Link to={link} className="btn btn-primary btn-sm">
            View Details
          </Link>
        )}
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="content-area">
        <div className="flex justify-center items-center h-64">
          <div className="spinner"></div>
          <span className="ml-2">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="content-area">
      <div className="mb-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Dashboard</h1>
            <p className="text-gray-600">Overview of your server infrastructure</p>
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
                Last updated: {lastUpdate.toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Servers"
          value={stats.totalServers}
          icon="fas fa-server"
          color="text-blue-500"
          link="/servers"
        />
        <StatCard
          title="Online Servers"
          value={stats.onlineServers}
          icon="fas fa-check-circle"
          color="text-green-500"
          link="/servers"
        />
        <StatCard
          title="Offline Servers"
          value={stats.offlineServers}
          icon="fas fa-times-circle"
          color="text-red-500"
          link="/servers"
        />
        <StatCard
          title="Active Alerts"
          value={stats.activeAlerts}
          icon="fas fa-bell"
          color="text-yellow-500"
          link="/alerts"
        />
      </div>

      {/* Recent Servers */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Recent Servers</h3>
          <Link to="/servers" className="btn btn-primary btn-sm">
            View All
          </Link>
        </div>
        
        {recentServers.length === 0 ? (
          <div className="text-center py-8">
            <i className="fas fa-server text-4xl text-gray-300 mb-4"></i>
            <p className="text-gray-500 mb-4">No servers configured yet</p>
            <Link to="/servers/new" className="btn btn-primary">
              <i className="fas fa-plus mr-2"></i>
              Add Your First Server
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>IP Address</th>
                  <th>Status</th>
                  <th>User</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {recentServers.map((server) => (
                  <tr key={server.id}>
                    <td>
                      <Link 
                        to={`/servers/${server.id}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {server.name}
                      </Link>
                    </td>
                    <td className="text-gray-600">{server.ip}:{server.port}</td>
                    <td>
                      <span className={`status-badge ${
                        server.status === 'active' ? 'status-online' : 'status-offline'
                      }`}>
                        {server.status}
                      </span>
                    </td>
                    <td className="text-gray-600">{server.user}</td>
                    <td>
                      <div className="flex space-x-2">
                        <Link 
                          to={`/servers/${server.id}`}
                          className="btn btn-sm btn-secondary"
                        >
                          <i className="fas fa-eye"></i>
                        </Link>
                        <button className="btn btn-sm btn-primary">
                          <i className="fas fa-play"></i>
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

      {/* Recent Alerts */}
      {alerts.length > 0 && (
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Recent Alerts</h3>
            <Link to="/alerts" className="btn btn-warning btn-sm">
              View All Alerts
            </Link>
          </div>
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div key={alert.id} className="flex items-center justify-between p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-center space-x-3">
                  <i className="fas fa-exclamation-triangle text-yellow-600"></i>
                  <div>
                    <div className="font-medium text-gray-900">{alert.title || alert.message}</div>
                    <div className="text-sm text-gray-600">
                      {alert.server_name && `Server: ${alert.server_name}`}
                      {alert.severity && ` • Severity: ${alert.severity}`}
                      {alert.created_at && ` • ${new Date(alert.created_at).toLocaleString()}`}
                    </div>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => apiService.acknowledgeAlert(alert.id).catch(console.error)}
                    title="Acknowledge Alert"
                  >
                    <i className="fas fa-check"></i>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <div className="card text-center">
          <i className="fas fa-plus-circle text-4xl text-blue-500 mb-4"></i>
          <h3 className="text-lg font-semibold mb-2">Add Server</h3>
          <p className="text-gray-600 mb-4">Connect a new server to start monitoring</p>
          <Link to="/servers/new" className="btn btn-primary">
            Add Server
          </Link>
        </div>
        
        <div className="card text-center">
          <i className="fas fa-chart-line text-4xl text-green-500 mb-4"></i>
          <h3 className="text-lg font-semibold mb-2">View Monitoring</h3>
          <p className="text-gray-600 mb-4">Check real-time performance metrics</p>
          <Link to="/monitoring" className="btn btn-success">
            View Metrics
          </Link>
        </div>
        
        <div className="card text-center">
          <i className="fas fa-cog text-4xl text-gray-500 mb-4"></i>
          <h3 className="text-lg font-semibold mb-2">Configure Alerts</h3>
          <p className="text-gray-600 mb-4">Set up notifications and thresholds</p>
          <Link to="/alerts" className="btn btn-secondary">
            Configure
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;