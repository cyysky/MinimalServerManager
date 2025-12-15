import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Sidebar = () => {
  const location = useLocation();

  const navItems = [
    { path: '/', icon: 'fas fa-tachometer-alt', label: 'Dashboard' },
    { path: '/servers', icon: 'fas fa-server', label: 'Servers' },
    { path: '/monitoring', icon: 'fas fa-chart-line', label: 'Monitoring' },
    { path: '/alerts', icon: 'fas fa-bell', label: 'Alerts' },
    { path: '/logs', icon: 'fas fa-file-alt', label: 'Logs' },
    { path: '/settings', icon: 'fas fa-cog', label: 'Settings' },
  ];

  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <aside className="sidebar">
      <nav>
        <ul className="sidebar-nav">
          {navItems.map((item) => (
            <li key={item.path}>
              <Link 
                to={item.path} 
                className={isActive(item.path) ? 'active' : ''}
              >
                <i className={item.icon}></i>
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      
      <div className="mt-8 px-4">
        <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">
          Quick Actions
        </div>
        <div className="space-y-2">
          <Link 
            to="/servers/new" 
            className="block w-full btn btn-primary btn-sm text-center"
          >
            <i className="fas fa-plus mr-1"></i>
            Add Server
          </Link>
          <Link 
            to="/websocket-test" 
            className="block w-full btn btn-secondary btn-sm text-center"
          >
            <i className="fas fa-plug mr-1"></i>
            Test Connection
          </Link>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;