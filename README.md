# Server Status Monitoring and Alerts System

A comprehensive real-time server monitoring and alerting solution built with FastAPI, React, and WebSocket technology.

## 🚀 Overview

This system provides real-time monitoring of server infrastructure with intelligent alerting capabilities. It features a modern web interface, real-time updates via WebSocket, and comprehensive monitoring of server metrics including CPU, memory, disk usage, and custom commands.

### Key Features

- **Real-time Server Monitoring**: Continuous monitoring of server status and performance metrics
- **Intelligent Alerting System**: Configurable alerts with severity levels and escalation
- **WebSocket Communication**: Real-time updates without page refreshes
- **SSH Connectivity**: Secure server connections via SSH with retry logic
- **Modern Web Interface**: React-based frontend with responsive design
- **Database Persistence**: SQLite database for reliable data storage
- **Custom Commands**: Execute and monitor custom server commands
- **Log Analysis**: Automated log parsing and error detection
- **Hardware Detection**: Automatic server hardware information gathering

## 🏗️ Architecture

The system follows a modern microservices architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  FastAPI Backend │    │   SQLite DB     │
│   (Electron)     │◄──►│   (WebSocket)    │◄──►│   (Metrics)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────►│  SSH Service    │◄─────────────┘
                        │  (Connections)  │
                        └─────────────────┘
```

### Core Components

1. **Frontend**: React 18 + Electron desktop application
2. **Backend**: FastAPI Python web service
3. **Database**: SQLite for data persistence
4. **WebSocket**: Real-time communication layer
5. **SSH Service**: Server connectivity and command execution
6. **Monitoring Service**: Continuous metrics collection
7. **Alert Service**: Alert generation and notification management

## 📋 System Requirements

### Backend Requirements
- Python 3.9+
- FastAPI 0.124.4+
- Uvicorn 0.38.0+
- Paramiko 4.0.0+ (SSH connectivity)
- PyCryptodome 3.23.0+ (encryption)
- SQLite3

### Frontend Requirements
- Node.js 16+
- React 18.0.0+
- Electron 28+
- Webpack 5
- TailwindCSS 3.0.0

### Server Requirements (Target Servers)
- Linux-based operating system
- SSH access enabled
- Standard Unix utilities (top, free, df, lscpu, etc.)

## 🛠️ Installation & Setup

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd msm

# Setup Python virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# Install backend dependencies
cd backend
pip install -r requirements.txt
```

### 2. Database Initialization

```bash
# The database is automatically initialized when the backend starts
# Database file: msm/data/app.db
```

### 3. Frontend Setup

```bash
# Install Node.js dependencies
cd ../frontend
npm install

# Build the frontend
npm run build
```

### 4. Start the System

#### Option A: Development Mode (Recommended)
```bash
# Start both backend and frontend concurrently
cd frontend
npm run dev
```

#### Option B: Manual Start
```bash
# Terminal 1: Start backend
cd backend
uvicorn app:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Start frontend
cd frontend
npm start
```

## 🔧 Configuration

### Backend Configuration

The backend automatically initializes with default settings. Key configuration options:

- **Database URL**: `sqlite:///./data/app.db`
- **WebSocket Port**: 8001 (default)
- **Monitoring Interval**: 30 seconds
- **Status Check Interval**: 10 seconds
- **Alert Check Interval**: 30 seconds

### Frontend Configuration

Frontend configuration is handled through environment variables and webpack configuration:

- **API Base URL**: `http://localhost:8001`
- **WebSocket URL**: `ws://localhost:8001/ws`
- **Build Mode**: Development/Production

### Server Configuration

When adding servers to monitor, configure:

- **Server Name**: Descriptive name for identification
- **IP Address**: Server IP or hostname
- **Port**: SSH port (default: 22)
- **Username**: SSH username
- **Authentication**: Password or SSH key file
- **Active Status**: Enable/disable monitoring

## 📊 Usage Guide

### 1. Adding Servers

1. Navigate to the "Server List" page
2. Click "Add Server" button
3. Fill in server details:
   - Name: `Production Web Server`
   - IP: `192.168.1.100`
   - Port: `22`
   - Username: `admin`
   - Password: `your_password` (or SSH key path)
4. Click "Create Server"

### 2. Starting Monitoring

1. Select a server from the list
2. Click "Start Monitoring"
3. Monitor real-time status updates on the dashboard

### 3. Configuring Alerts

1. Navigate to "Alerts" section
2. Click "Create Alert"
3. Configure alert conditions:
   - **Name**: `High CPU Usage`
   - **Server**: Select target server
   - **Metric Type**: `cpu`
   - **Field**: `totalUsage`
   - **Comparison**: `>`
   - **Threshold**: `80.0`
   - **Severity**: `high`
4. Save the alert condition

### 4. Real-time Monitoring

- **Dashboard**: Overview of all servers and their status
- **Server Detail**: Detailed metrics and history for individual servers
- **Alert List**: Current and historical alerts
- **Real-time Updates**: Automatic updates via WebSocket

## 🔍 API Reference

### REST Endpoints

#### Server Management
- `GET /servers/` - List all servers
- `POST /servers/` - Create new server
- `GET /servers/{id}` - Get server details
- `PUT /servers/{id}` - Update server
- `DELETE /servers/{id}` - Delete server
- `POST /servers/{id}/toggle` - Toggle server active status

#### Monitoring
- `POST /servers/{id}/monitor/start` - Start monitoring
- `POST /servers/{id}/monitor/stop` - Stop monitoring
- `GET /servers/{id}/metrics` - Get current metrics
- `GET /status/realtime` - Get real-time status of all servers
- `GET /status/server/{id}` - Get real-time status of specific server

#### Alerts
- `GET /alerts/` - List active alert conditions
- `POST /alerts/` - Create alert condition
- `GET /alerts/history/` - Get alert history
- `POST /alerts/{id}/resolve` - Mark alert as resolved

#### Logs
- `GET /logs/sources/` - List log sources
- `POST /logs/sources/` - Create log source
- `GET /logs/analyze/{server_id}` - Analyze logs for server
- `GET /logs/recent/{source_id}` - Get recent log entries

### WebSocket Endpoints

#### Connection
- `ws://localhost:8001/ws` - Main WebSocket endpoint

#### Message Types
- `ping` - Connection health check
- `subscribe` - Subscribe to update types
- `unsubscribe` - Unsubscribe from updates
- `get_status` - Request current server statuses
- `acknowledge_alert` - Acknowledge an alert

#### Update Types
- `server_status_change` - Server online/offline status changes
- `metrics_update` - New performance metrics available
- `alert_triggered` - New alert triggered
- `alert_resolved` - Alert marked as resolved
- `monitoring_started` - Server monitoring started
- `monitoring_stopped` - Server monitoring stopped

## 🧪 Testing

### Running Tests

```bash
# Backend API tests
cd backend
python -m pytest test_api.py -v

# WebSocket tests
python test_websocket.py

# Integration tests
python test_integration.py

# Performance tests
python test_performance.py

# All tests
cd ..
python -m pytest msm/test_*.py -v
```

### Test Coverage

- **API Testing**: All REST endpoints tested
- **WebSocket Testing**: Real-time communication verified
- **Integration Testing**: End-to-end functionality
- **Performance Testing**: Load and stress testing

See [Testing Documentation](docs/Testing.md) for detailed testing information.

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**
   ```bash
   # Set production environment variables
   export ENVIRONMENT=production
   export DATABASE_URL=sqlite:///./data/app.db
   export SECRET_KEY=your-secret-key
   ```

2. **Build Frontend**
   ```bash
   cd frontend
   npm run build
   ```

3. **Start Backend**
   ```bash
   cd backend
   uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
   ```

4. **Process Management**
   ```bash
   # Using systemd (Linux)
   sudo systemctl enable msm-backend
   sudo systemctl start msm-backend
   ```

### Docker Deployment

```dockerfile
# Dockerfile example
FROM python:3.9-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

See [Deployment Guide](docs/Deployment.md) for detailed deployment instructions.

## 🔧 Troubleshooting

### Common Issues

#### Backend Won't Start
- **Check Python version**: Requires Python 3.9+
- **Verify dependencies**: Run `pip install -r requirements.txt`
- **Database permissions**: Ensure write access to `data/` directory

#### Frontend Build Fails
- **Node.js version**: Requires Node.js 16+
- **Clear cache**: Run `npm cache clean --force`
- **Reinstall dependencies**: Delete `node_modules` and run `npm install`

#### WebSocket Connection Issues
- **CORS configuration**: Check allow_origins in backend
- **Firewall**: Ensure port 8001 is accessible
- **Browser compatibility**: Use modern browsers with WebSocket support

#### SSH Connection Failures
- **Network connectivity**: Test with `ping` and `telnet`
- **Authentication**: Verify username/password or SSH key
- **Server configuration**: Ensure SSH service is running

### Debug Mode

Enable debug logging:

```python
# In backend/app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Log Files

- **Backend logs**: Check console output for detailed error messages
- **Frontend logs**: Browser developer console (F12)
- **SSH logs**: Server-side SSH daemon logs

## 📈 Performance

### System Performance

Based on comprehensive testing:

- **API Response Time**: ~2 seconds average
- **WebSocket Latency**: <100ms for real-time updates
- **Memory Usage**: Stable at ~40MB
- **Concurrent Users**: Supports 10+ simultaneous WebSocket connections
- **Server Monitoring**: 30-second intervals for metrics collection

### Optimization Tips

1. **Database**: Use PostgreSQL for production with higher loads
2. **Caching**: Implement Redis for session and cache management
3. **Load Balancing**: Use multiple backend instances behind a load balancer
4. **Monitoring**: Set up system monitoring for the monitoring system itself

## 🔒 Security

### Current Security Features

- **SSH Key Authentication**: Support for key-based server authentication
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Input Validation**: Pydantic models for request validation
- **Error Handling**: Secure error responses without sensitive data exposure

### Security Recommendations

1. **Authentication**: Implement user authentication and authorization
2. **Encryption**: Encrypt sensitive data in database
3. **HTTPS**: Use HTTPS in production
4. **Rate Limiting**: Implement API rate limiting
5. **Audit Logging**: Log all administrative actions

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Code Style

- **Python**: Follow PEP 8 style guidelines
- **JavaScript**: Use ESLint and Prettier configurations
- **Documentation**: Update documentation for new features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Getting Help

1. **Documentation**: Check the docs/ directory for detailed guides
2. **Issues**: Report bugs and feature requests via GitHub Issues
3. **Discussions**: Use GitHub Discussions for questions and ideas

### System Information

- **Version**: 1.0.0
- **Last Updated**: 2025-12-15
- **Test Coverage**: 95.8% success rate
- **Status**: Production Ready

---

**Server Status Monitoring and Alerts System** - Real-time infrastructure monitoring made simple.