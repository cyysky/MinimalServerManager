import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './styles/global.css';

// Import pages
import ServerList from './pages/ServerList';
import ServerDetail from './pages/ServerDetail';
import ServerCreate from './pages/ServerCreate';
import Settings from './pages/Settings';
import Dashboard from './pages/Dashboard';
import Monitoring from './pages/Monitoring';
import WebSocketTest from './components/WebSocketTest';

// Import components
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import AlertManager from './components/AlertManager';
import AlertList from './components/AlertList';

function App() {
  return (
    <Router>
      <div className="app-container">
        <Navbar />
        <div className="main-content">
          <Sidebar />
          <div className="content-area">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/servers" element={<ServerList />} />
              <Route path="/servers/new" element={<ServerCreate />} />
              <Route path="/servers/:id" element={<ServerDetail />} />
              <Route path="/monitoring" element={<Monitoring />} />
              <Route path="/alerts" element={<AlertList />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/websocket-test" element={<WebSocketTest />} />
            </Routes>
          </div>
        </div>
        {/* Alert Manager - renders notifications globally */}
        <AlertManager />
      </div>
    </Router>
  );
}

export default App;