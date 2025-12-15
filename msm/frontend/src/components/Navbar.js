import React from 'react';
import { Link } from 'react-router-dom';

const Navbar = () => {
  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <i className="fas fa-server mr-2"></i>
        Minimal Server Manager
      </Link>
      
      <div className="navbar-actions">
        <div className="flex items-center space-x-4">
          <div className="text-sm">
            <span className="text-gray-200">Status: </span>
            <span className="status-badge status-online">Connected</span>
          </div>
          
          <button className="btn btn-sm btn-secondary">
            <i className="fas fa-cog mr-1"></i>
            Settings
          </button>
          
          <button className="btn btn-sm btn-secondary">
            <i className="fas fa-question-circle mr-1"></i>
            Help
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;