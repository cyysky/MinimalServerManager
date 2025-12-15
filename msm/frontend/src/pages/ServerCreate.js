import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import apiService from '../services/apiService';

const ServerCreate = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    ip: '',
    port: 22,
    user: '',
    ssh_key_path: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionTestResult, setConnectionTestResult] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const testConnection = async () => {
    if (!formData.ip || !formData.user) {
      alert('Please fill in IP address and username before testing connection');
      return;
    }

    setTestingConnection(true);
    setConnectionTestResult(null);

    try {
      // Create a temporary server object for testing
      const testServer = {
        name: 'Test Connection',
        ip: formData.ip,
        port: parseInt(formData.port),
        user: formData.user,
        ssh_key_path: formData.ssh_key_path || null,
        password: formData.password || null
      };

      // First create the server
      const server = await apiService.createServer(testServer);
      
      // Then test the connection by getting metrics
      try {
        const metrics = await apiService.getServerMetrics(server.id);
        setConnectionTestResult({
          success: true,
          message: 'Connection successful! Server is reachable.',
          data: metrics
        });
      } catch (metricsError) {
        setConnectionTestResult({
          success: false,
          message: 'Server created but connection test failed. Please check credentials.',
          error: metricsError.message
        });
      }

      // Clean up the test server
      await apiService.deleteServer(server.id);
      
    } catch (error) {
      setConnectionTestResult({
        success: false,
        message: 'Connection test failed',
        error: error.message
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name || !formData.ip || !formData.user) {
      alert('Please fill in all required fields');
      return;
    }

    setLoading(true);

    try {
      const serverData = {
        name: formData.name,
        ip: formData.ip,
        port: parseInt(formData.port),
        user: formData.user,
        ssh_key_path: formData.ssh_key_path || null,
        password: formData.password || null
      };

      await apiService.createServer(serverData);
      navigate('/servers');
    } catch (error) {
      console.error('Error creating server:', error);
      alert('Failed to create server: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="content-area">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center space-x-4">
          <Link to="/servers" className="btn btn-secondary btn-sm">
            <i className="fas fa-arrow-left mr-2"></i>
            Back to Servers
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Add New Server</h1>
            <p className="text-gray-600">Configure a new server for monitoring</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Form */}
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Server Configuration</h3>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Server Name */}
                <div>
                  <label className="form-label">Server Name *</label>
                  <input
                    type="text"
                    name="name"
                    className="form-input"
                    value={formData.name}
                    onChange={handleChange}
                    placeholder="e.g., Web Server 1"
                    required
                  />
                </div>

                {/* IP Address */}
                <div>
                  <label className="form-label">IP Address *</label>
                  <input
                    type="text"
                    name="ip"
                    className="form-input"
                    value={formData.ip}
                    onChange={handleChange}
                    placeholder="192.168.1.100"
                    required
                  />
                </div>

                {/* Port */}
                <div>
                  <label className="form-label">SSH Port</label>
                  <input
                    type="number"
                    name="port"
                    className="form-input"
                    value={formData.port}
                    onChange={handleChange}
                    min="1"
                    max="65535"
                  />
                </div>

                {/* Username */}
                <div>
                  <label className="form-label">Username *</label>
                  <input
                    type="text"
                    name="user"
                    className="form-input"
                    value={formData.user}
                    onChange={handleChange}
                    placeholder="e.g., ubuntu, root"
                    required
                  />
                </div>

                {/* SSH Key Path */}
                <div className="md:col-span-2">
                  <label className="form-label">SSH Key Path (optional)</label>
                  <input
                    type="text"
                    name="ssh_key_path"
                    className="form-input"
                    value={formData.ssh_key_path}
                    onChange={handleChange}
                    placeholder="/path/to/private/key"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Leave empty to use password authentication
                  </p>
                </div>

                {/* Password */}
                <div className="md:col-span-2">
                  <label className="form-label">Password (optional)</label>
                  <input
                    type="password"
                    name="password"
                    className="form-input"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="Enter password if not using SSH keys"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Leave empty if using SSH key authentication
                  </p>
                </div>
              </div>

              <div className="flex justify-between items-center mt-8">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => navigate('/servers')}
                >
                  Cancel
                </button>
                
                <div className="flex space-x-3">
                  <button
                    type="button"
                    className="btn btn-info"
                    onClick={testConnection}
                    disabled={testingConnection || !formData.ip || !formData.user}
                  >
                    {testingConnection ? (
                      <>
                        <div className="spinner mr-2"></div>
                        Testing...
                      </>
                    ) : (
                      <>
                        <i className="fas fa-plug mr-2"></i>
                        Test Connection
                      </>
                    )}
                  </button>
                  
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <div className="spinner mr-2"></div>
                        Creating...
                      </>
                    ) : (
                      <>
                        <i className="fas fa-plus mr-2"></i>
                        Create Server
                      </>
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Connection Test Result */}
          {connectionTestResult && (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Connection Test</h3>
              </div>
              <div className="p-4">
                <div className={`flex items-center mb-3 ${
                  connectionTestResult.success ? 'text-green-600' : 'text-red-600'
                }`}>
                  <i className={`fas ${
                    connectionTestResult.success ? 'fa-check-circle' : 'fa-times-circle'
                  } mr-2`}></i>
                  <span className="font-medium">
                    {connectionTestResult.success ? 'Success' : 'Failed'}
                  </span>
                </div>
                <p className="text-sm text-gray-600 mb-2">
                  {connectionTestResult.message}
                </p>
                {connectionTestResult.error && (
                  <p className="text-xs text-red-500">
                    Error: {connectionTestResult.error}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Help */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Connection Help</h3>
            </div>
            <div className="p-4 text-sm text-gray-600">
              <div className="space-y-3">
                <div>
                  <h4 className="font-medium text-gray-900">SSH Key Authentication</h4>
                  <p>Recommended for better security. Provide the path to your private key file.</p>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">Password Authentication</h4>
                  <p>Simpler setup but less secure. Use strong passwords.</p>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">Port</h4>
                  <p>Default SSH port is 22. Change if your server uses a different port.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServerCreate;