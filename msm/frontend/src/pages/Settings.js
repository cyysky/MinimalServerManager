import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Settings = () => {
  const [settings, setSettings] = useState({
    telegram: {
      bot_token: '',
      chat_id: '',
      enabled: false
    },
    monitoring: {
      interval: 60,
      retention_days: 30
    },
    alerts: {
      default_cooldown: 10,
      email_notifications: true
    }
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('general');

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      // TODO: Implement settings API endpoints
      // For now, using default settings
    } catch (error) {
      console.error('Error fetching settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    try {
      setSaving(true);
      // TODO: Implement settings API endpoints
      alert('Settings saved successfully!');
    } catch (error) {
      console.error('Error saving settings:', error);
      alert('Error saving settings');
    } finally {
      setSaving(false);
    }
  };

  const testTelegramConnection = async () => {
    try {
      // TODO: Implement Telegram test endpoint
      alert('Telegram test functionality will be implemented');
    } catch (error) {
      console.error('Error testing Telegram connection:', error);
    }
  };

  const tabs = [
    { id: 'general', label: 'General', icon: 'fas fa-cog' },
    { id: 'monitoring', label: 'Monitoring', icon: 'fas fa-chart-line' },
    { id: 'alerts', label: 'Alerts', icon: 'fas fa-bell' },
    { id: 'notifications', label: 'Notifications', icon: 'fas fa-envelope' },
  ];

  if (loading) {
    return (
      <div className="content-area">
        <div className="flex justify-center items-center h-64">
          <div className="spinner"></div>
          <span className="ml-2">Loading settings...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="content-area">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Settings</h1>
          <p className="text-gray-600">Configure your server manager preferences</p>
        </div>
        <button 
          className="btn btn-primary"
          onClick={saveSettings}
          disabled={saving}
        >
          {saving ? (
            <div className="spinner mr-2"></div>
          ) : (
            <i className="fas fa-save mr-2"></i>
          )}
          Save Settings
        </button>
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
          {/* General Tab */}
          {activeTab === 'general' && (
            <div className="space-y-6">
              <div>
                <h4 className="text-lg font-semibold mb-4">Application Settings</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="form-group">
                    <label className="form-label">Application Name</label>
                    <input 
                      type="text" 
                      className="form-input"
                      defaultValue="Minimal Server Manager"
                      readOnly
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Version</label>
                    <input 
                      type="text" 
                      className="form-input"
                      defaultValue="1.0.0"
                      readOnly
                    />
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-lg font-semibold mb-4">Database Settings</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="form-group">
                    <label className="form-label">Database Path</label>
                    <input 
                      type="text" 
                      className="form-input"
                      defaultValue="./data/app.db"
                      readOnly
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Database Type</label>
                    <select className="form-select" defaultValue="sqlite" readOnly>
                      <option value="sqlite">SQLite</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Monitoring Tab */}
          {activeTab === 'monitoring' && (
            <div className="space-y-6">
              <div>
                <h4 className="text-lg font-semibold mb-4">Monitoring Configuration</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="form-group">
                    <label className="form-label">Monitoring Interval (seconds)</label>
                    <input 
                      type="number" 
                      className="form-input"
                      value={settings.monitoring.interval}
                      onChange={(e) => setSettings({
                        ...settings,
                        monitoring: {
                          ...settings.monitoring,
                          interval: parseInt(e.target.value)
                        }
                      })}
                      min="10"
                      max="3600"
                    />
                    <small className="text-gray-500">How often to collect metrics (10-3600 seconds)</small>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Data Retention (days)</label>
                    <input 
                      type="number" 
                      className="form-input"
                      value={settings.monitoring.retention_days}
                      onChange={(e) => setSettings({
                        ...settings,
                        monitoring: {
                          ...settings.monitoring,
                          retention_days: parseInt(e.target.value)
                        }
                      })}
                      min="1"
                      max="365"
                    />
                    <small className="text-gray-500">How long to keep historical data (1-365 days)</small>
                  </div>
                </div>
              </div>

              <div className="alert alert-info">
                <i className="fas fa-info-circle mr-2"></i>
                <strong>Note:</strong> Changes to monitoring settings will affect all servers. Existing data will be preserved.
              </div>
            </div>
          )}

          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className="space-y-6">
              <div>
                <h4 className="text-lg font-semibold mb-4">Alert Configuration</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="form-group">
                    <label className="form-label">Default Cooldown (minutes)</label>
                    <input 
                      type="number" 
                      className="form-input"
                      value={settings.alerts.default_cooldown}
                      onChange={(e) => setSettings({
                        ...settings,
                        alerts: {
                          ...settings.alerts,
                          default_cooldown: parseInt(e.target.value)
                        }
                      })}
                      min="1"
                      max="60"
                    />
                    <small className="text-gray-500">Minimum time between alert notifications</small>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Email Notifications</label>
                    <div className="flex items-center mt-2">
                      <input 
                        type="checkbox" 
                        className="mr-2"
                        checked={settings.alerts.email_notifications}
                        onChange={(e) => setSettings({
                          ...settings,
                          alerts: {
                            ...settings.alerts,
                            email_notifications: e.target.checked
                          }
                        })}
                      />
                      <span className="text-gray-700">Enable email notifications</span>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-lg font-semibold mb-4">Default Alert Thresholds</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="form-group">
                    <label className="form-label">CPU Usage (%)</label>
                    <input 
                      type="number" 
                      className="form-input"
                      defaultValue="80"
                      min="0"
                      max="100"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Memory Usage (%)</label>
                    <input 
                      type="number" 
                      className="form-input"
                      defaultValue="85"
                      min="0"
                      max="100"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Disk Usage (%)</label>
                    <input 
                      type="number" 
                      className="form-input"
                      defaultValue="90"
                      min="0"
                      max="100"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <div className="space-y-6">
              <div>
                <h4 className="text-lg font-semibold mb-4">Telegram Configuration</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="form-group">
                    <label className="form-label">Bot Token</label>
                    <input 
                      type="password" 
                      className="form-input"
                      value={settings.telegram.bot_token}
                      onChange={(e) => setSettings({
                        ...settings,
                        telegram: {
                          ...settings.telegram,
                          bot_token: e.target.value
                        }
                      })}
                      placeholder="Enter your Telegram bot token"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Chat ID</label>
                    <input 
                      type="text" 
                      className="form-input"
                      value={settings.telegram.chat_id}
                      onChange={(e) => setSettings({
                        ...settings,
                        telegram: {
                          ...settings.telegram,
                          chat_id: e.target.value
                        }
                      })}
                      placeholder="Enter your Telegram chat ID"
                    />
                  </div>
                </div>
                <div className="flex items-center mt-4">
                  <input 
                    type="checkbox" 
                    className="mr-2"
                    checked={settings.telegram.enabled}
                    onChange={(e) => setSettings({
                      ...settings,
                      telegram: {
                        ...settings.telegram,
                        enabled: e.target.checked
                      }
                    })}
                  />
                  <span className="text-gray-700">Enable Telegram notifications</span>
                </div>
                <div className="mt-4">
                  <button 
                    className="btn btn-secondary btn-sm"
                    onClick={testTelegramConnection}
                  >
                    <i className="fas fa-paper-plane mr-2"></i>
                    Test Connection
                  </button>
                </div>
              </div>

              <div className="alert alert-warning">
                <i className="fas fa-exclamation-triangle mr-2"></i>
                <strong>Security Note:</strong> Bot tokens are sensitive information. Keep them secure and never share them publicly.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Settings;