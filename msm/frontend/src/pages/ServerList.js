import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import apiService from '../services/apiService';
import websocketService from '../utils/websocketService';

const ServerList = () => {
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [wsStatus, setWsStatus] = useState('disconnected');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    fetchServers();
    
    // Connect to WebSocket for real-time updates
    initializeWebSocket();
    
    // Set up periodic refresh as fallback
    const refreshInterval = setInterval(() => {
      if (autoRefresh) {
        fetchServers();
      }
    }, 30000); // Refresh every 30 seconds

    return () => {
      clearInterval(refreshInterval);
      cleanupWebSocket();
    };
  }, [autoRefresh]);

  const initializeWebSocket = async () => {
    try {
      setWsStatus('connecting');
      await websocketService.connect();
      setWsStatus('connected');
      
      // Subscribe to server updates
      websocketService.subscribe('server_status');
      websocketService.subscribe('server_metrics');
      
      // Set up message handlers
      websocketService.onMessage('server_status_update', handleServerStatusUpdate);
      websocketService.onMessage('server_metrics_update', handleServerMetricsUpdate);
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
    websocketService.offMessage('server_created', handleServerUpdate);
    websocketService.offMessage('server_updated', handleServerUpdate);
    websocketService.offMessage('server_deleted', handleServerUpdate);
    websocketService.offMessage('connection_failed', handleConnectionFailed);
  };

  const handleServerStatusUpdate = (data) => {
    console.log('Server status updated:', data);
    setLastUpdate(new Date());
    // Update server status in the list without full refresh
    setServers(prev => prev.map(server =>
      server.id === data.server_id
        ? { ...server, status: data.status, updated_at: data.timestamp }
        : server
    ));
  };

  const handleServerMetricsUpdate = (data) => {
    console.log('Server metrics updated:', data);
    setLastUpdate(new Date());
    // Update metrics in the server object
    setServers(prev => prev.map(server =>
      server.id === data.server_id
        ? { ...server, last_metrics: data.metrics, updated_at: data.timestamp }
        : server
    ));
  };

  const handleConnectionFailed = () => {
    setWsStatus('error');
  };

  const handleServerUpdate = () => {
    fetchServers();
  };

  const fetchServers = async () => {
    try {
      setLoading(true);
      const servers = await apiService.getServers();
      setServers(servers);
    } catch (error) {
      console.error('Error fetching servers:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleServerStatus = async (serverId) => {
    try {
      await apiService.toggleServerStatus(serverId);
      // WebSocket will handle the update
    } catch (error) {
      console.error('Error toggling server status:', error);
    }
  };

  const deleteServer = async (serverId) => {
    if (window.confirm('Are you sure you want to delete this server?')) {
      try {
        await apiService.deleteServer(serverId);
        // WebSocket will handle the update
      } catch (error) {
        console.error('Error deleting server:', error);
      }
    }
  };

  const filteredServers = servers.filter(server => {
    const matchesSearch = server.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         server.ip.includes(searchTerm);
    const matchesFilter = filterStatus === 'all' || server.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  if (loading) {
    return (
      <div className="content-area">
        <div className="flex justify-center items-center h-64">
          <div className="spinner"></div>
          <span className="ml-2">Loading servers...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="content-area">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Servers</h1>
          <p className="text-gray-600">Manage your server infrastructure</p>
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
          {/* Auto Refresh Toggle */}
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="autoRefresh"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="form-checkbox"
            />
            <label htmlFor="autoRefresh" className="text-sm text-gray-600">Auto-refresh</label>
          </div>
          {/* Last Update Time */}
          {lastUpdate && (
            <div className="text-sm text-gray-500">
              Updated: {lastUpdate.toLocaleTimeString()}
            </div>
          )}
          <Link to="/servers/new" className="btn btn-primary">
            <i className="fas fa-plus mr-2"></i>
            Add Server
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="card mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search servers by name or IP..."
              className="form-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="md:w-48">
            <select
              className="form-select"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>
      </div>

      {/* Servers Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            Server List ({filteredServers.length} of {servers.length})
          </h3>
        </div>

        {filteredServers.length === 0 ? (
          <div className="text-center py-12">
            {servers.length === 0 ? (
              <>
                <i className="fas fa-server text-6xl text-gray-300 mb-4"></i>
                <h3 className="text-xl font-semibold text-gray-600 mb-2">No servers configured</h3>
                <p className="text-gray-500 mb-6">Get started by adding your first server</p>
                <Link to="/servers/new" className="btn btn-primary">
                  <i className="fas fa-plus mr-2"></i>
                  Add Your First Server
                </Link>
              </>
            ) : (
              <>
                <i className="fas fa-search text-4xl text-gray-300 mb-4"></i>
                <h3 className="text-lg font-semibold text-gray-600 mb-2">No servers found</h3>
                <p className="text-gray-500">Try adjusting your search or filter criteria</p>
              </>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>IP Address</th>
                  <th>Port</th>
                  <th>User</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredServers.map((server) => (
                  <tr key={server.id}>
                    <td>
                      <Link 
                        to={`/servers/${server.id}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {server.name}
                      </Link>
                    </td>
                    <td className="text-gray-600 font-mono">{server.ip}</td>
                    <td className="text-gray-600">{server.port}</td>
                    <td className="text-gray-600">{server.user}</td>
                    <td>
                      <span className={`status-badge ${
                        server.status === 'active' ? 'status-online' : 'status-offline'
                      }`}>
                        {server.status}
                      </span>
                    </td>
                    <td className="text-gray-600">
                      {new Date(server.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      <div className="flex space-x-2">
                        <Link 
                          to={`/servers/${server.id}`}
                          className="btn btn-sm btn-secondary"
                          title="View Details"
                        >
                          <i className="fas fa-eye"></i>
                        </Link>
                        <button 
                          className={`btn btn-sm ${
                            server.status === 'active' ? 'btn-warning' : 'btn-success'
                          }`}
                          title={server.status === 'active' ? 'Deactivate' : 'Activate'}
                          onClick={() => toggleServerStatus(server.id)}
                        >
                          <i className={`fas ${server.status === 'active' ? 'fa-pause' : 'fa-play'}`}></i>
                        </button>
                        <button 
                          className="btn btn-sm btn-danger"
                          title="Delete Server"
                          onClick={() => deleteServer(server.id)}
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        <div className="card text-center">
          <i className="fas fa-server text-3xl text-blue-500 mb-2"></i>
          <div className="text-2xl font-bold text-gray-900">{servers.length}</div>
          <div className="text-gray-600">Total Servers</div>
        </div>
        <div className="card text-center">
          <i className="fas fa-check-circle text-3xl text-green-500 mb-2"></i>
          <div className="text-2xl font-bold text-gray-900">
            {servers.filter(s => s.status === 'active').length}
          </div>
          <div className="text-gray-600">Active Servers</div>
        </div>
        <div className="card text-center">
          <i className="fas fa-times-circle text-3xl text-red-500 mb-2"></i>
          <div className="text-2xl font-bold text-gray-900">
            {servers.filter(s => s.status === 'inactive').length}
          </div>
          <div className="text-gray-600">Inactive Servers</div>
        </div>
      </div>
    </div>
  );
};

export default ServerList;