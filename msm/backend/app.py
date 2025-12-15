import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import uvicorn
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

app = FastAPI(
    title="Minimal Server Manager API",
    description="Backend API for server monitoring and management",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info = {}  # websocket: {"user_id": int, "subscriptions": list}
        self._lock = threading.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None):
        await websocket.accept()
        with self._lock:
            self.active_connections.append(websocket)
            self.connection_info[websocket] = {
                "user_id": user_id,
                "subscriptions": ["all"],  # Default subscription
                "connected_at": datetime.utcnow()
            }
        print(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            if websocket in self.connection_info:
                del self.connection_info[websocket]
        print(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str, message_type: str = "update", target_subscriptions: List[str] = None):
        """
        Broadcast message to connections with matching subscriptions
        """
        # Handle the message data safely
        try:
            if isinstance(message, str) and message.strip():
                data = json.loads(message)
            elif isinstance(message, str) and not message.strip():
                data = {"message": message}
            else:
                data = message
        except json.JSONDecodeError:
            data = {"message": message}
        
        payload = {
            "type": message_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        json_message = json.dumps(payload)
        
        disconnected = []
        with self._lock:
            connections = self.active_connections.copy()
        
        for connection in connections:
            try:
                # Check if connection should receive this message
                should_send = True
                if target_subscriptions:
                    conn_info = self.connection_info.get(connection, {})
                    subscriptions = conn_info.get("subscriptions", [])
                    should_send = any(sub in subscriptions for sub in target_subscriptions)
                
                if should_send:
                    await connection.send_text(json_message)
                    
            except Exception as e:
                print(f"Error sending message to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)
    
    def subscribe(self, websocket: WebSocket, subscription_type: str):
        """Subscribe a connection to specific updates"""
        with self._lock:
            if websocket in self.connection_info:
                subscriptions = self.connection_info[websocket]["subscriptions"]
                if subscription_type not in subscriptions:
                    subscriptions.append(subscription_type)
    
    def unsubscribe(self, websocket: WebSocket, subscription_type: str):
        """Unsubscribe a connection from specific updates"""
        with self._lock:
            if websocket in self.connection_info:
                subscriptions = self.connection_info[websocket]["subscriptions"]
                if subscription_type in subscriptions:
                    subscriptions.remove(subscription_type)
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        with self._lock:
            return len(self.active_connections)

manager = ConnectionManager()

# Database setup
from database import get_database_url, init_db
SQLALCHEMY_DATABASE_URL = get_database_url()

# Initialize database
engine = init_db(SQLALCHEMY_DATABASE_URL)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models after engine is created
from models import Base, Server, ServerSpec

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Initialize services
from services.ssh_service import ssh_service
from services.monitoring_service import init_monitoring_service
from services.alert_service import init_alert_service
from services.log_service import init_log_service

# Initialize all services with WebSocket manager
monitoring_service = init_monitoring_service(SQLALCHEMY_DATABASE_URL, manager)
alert_service = init_alert_service(SQLALCHEMY_DATABASE_URL, manager)
log_service = init_log_service(SQLALCHEMY_DATABASE_URL)

# Start monitoring and alert services
monitoring_service.start()
alert_service.start()

# Pydantic models for request/response
class ServerCreate(BaseModel):
    name: str
    ip: str
    port: int = 22
    user: str
    ssh_key_path: Optional[str] = None
    password: Optional[str] = None

class ServerResponse(BaseModel):
    id: int
    name: str
    ip: str
    port: int
    user: str
    status: str
    created_at: datetime
    updated_at: datetime

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    ssh_key_path: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

@app.get("/")
async def root():
    return {"message": "Minimal Server Manager API"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "websocket_connections": manager.get_connection_count(),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_personal_message(
                    json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                        "server_time": datetime.utcnow().isoformat()
                    }),
                    websocket
                )
            elif message.get("type") == "subscribe":
                # Client wants to subscribe to specific updates
                subscriptions = message.get("subscriptions", ["all"])
                for sub in subscriptions:
                    manager.subscribe(websocket, sub)
                
                await manager.send_personal_message(
                    json.dumps({
                        "type": "subscribed",
                        "status": "success",
                        "subscriptions": subscriptions
                    }),
                    websocket
                )
            elif message.get("type") == "unsubscribe":
                # Client wants to unsubscribe from specific updates
                subscriptions = message.get("subscriptions", [])
                for sub in subscriptions:
                    manager.unsubscribe(websocket, sub)
                
                await manager.send_personal_message(
                    json.dumps({
                        "type": "unsubscribed",
                        "status": "success",
                        "subscriptions": subscriptions
                    }),
                    websocket
                )
            elif message.get("type") == "get_status":
                # Client wants current server statuses
                statuses = monitoring_service.get_all_server_statuses()
                await manager.send_personal_message(
                    json.dumps({
                        "type": "server_statuses",
                        "data": statuses,
                        "timestamp": datetime.utcnow().isoformat()
                    }),
                    websocket
                )
            elif message.get("type") == "acknowledge_alert":
                # Client acknowledges an alert
                alert_id = message.get("alert_id")
                if alert_id:
                    success = alert_service.mark_alert_resolved(alert_id)
                    if success:
                        await manager.broadcast(
                            json.dumps({
                                "type": "alert_acknowledged",
                                "alert_id": alert_id,
                                "timestamp": datetime.utcnow().isoformat()
                            }),
                            "alert_update"
                        )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except json.JSONDecodeError:
        await manager.send_personal_message(
            json.dumps({"type": "error", "message": "Invalid JSON"}),
            websocket
        )
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Server endpoints
@app.post("/servers/", response_model=ServerResponse)
async def create_server(server: ServerCreate):
    """Create a new server"""
    db = SessionLocal()
    try:
        # Create server record
        db_server = Server(
            name=server.name,
            ip=server.ip,
            port=server.port,
            user=server.user,
            ssh_key_path=server.ssh_key_path,
            password_encrypted=server.password,  # Note: In production, encrypt this
            is_active=True
        )
        
        db.add(db_server)
        db.commit()
        db.refresh(db_server)
        
        # Create associated ServerSpec record
        db_spec = ServerSpec(server_id=db_server.id)
        db.add(db_spec)
        db.commit()
        
        # Broadcast new server creation
        await manager.broadcast(f"New server created: {server.name}", "server_created")
        
        return {
            "id": db_server.id,
            "name": db_server.name,
            "ip": db_server.ip,
            "port": db_server.port,
            "user": db_server.user,
            "status": "active" if db_server.is_active else "inactive",
            "created_at": db_server.created_at,
            "updated_at": db_server.updated_at
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/servers/", response_model=List[ServerResponse])
async def list_servers():
    """List all servers"""
    db = SessionLocal()
    try:
        servers = db.query(Server).all()
        return [{
            "id": server.id,
            "name": server.name,
            "ip": server.ip,
            "port": server.port,
            "user": server.user,
            "status": "active" if server.is_active else "inactive",
            "created_at": server.created_at,
            "updated_at": server.updated_at
        } for server in servers]
    finally:
        db.close()

@app.get("/servers/{server_id}", response_model=ServerResponse)
async def get_server(server_id: int):
    """Get a specific server by ID"""
    db = SessionLocal()
    try:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        return {
            "id": server.id,
            "name": server.name,
            "ip": server.ip,
            "port": server.port,
            "user": server.user,
            "status": "active" if server.is_active else "inactive",
            "created_at": server.created_at,
            "updated_at": server.updated_at
        }
    finally:
        db.close()

@app.put("/servers/{server_id}", response_model=ServerResponse)
async def update_server(server_id: int, server_update: ServerUpdate):
    """Update a server"""
    db = SessionLocal()
    try:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Update fields if provided
        if server_update.name is not None:
            server.name = server_update.name
        if server_update.ip is not None:
            server.ip = server_update.ip
        if server_update.port is not None:
            server.port = server_update.port
        if server_update.user is not None:
            server.user = server_update.user
        if server_update.ssh_key_path is not None:
            server.ssh_key_path = server_update.ssh_key_path
        if server_update.password is not None:
            server.password_encrypted = server_update.password  # Note: In production, encrypt this
        
        server.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(server)
        
        # Broadcast server update
        await manager.broadcast(f"Server updated: {server.name}", "server_updated")
        
        return {
            "id": server.id,
            "name": server.name,
            "ip": server.ip,
            "port": server.port,
            "user": server.user,
            "status": "active" if server.is_active else "inactive",
            "created_at": server.created_at,
            "updated_at": server.updated_at
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/servers/{server_id}", response_model=dict)
async def delete_server(server_id: int):
    """Delete a server"""
    db = SessionLocal()
    try:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        server_name = server.name
        db.delete(server)
        db.commit()
        
        # Broadcast server deletion
        await manager.broadcast(f"Server deleted: {server_name}", "server_deleted")
        
        return {"message": "Server deleted successfully", "id": server_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/servers/{server_id}/toggle", response_model=ServerResponse)
async def toggle_server_status(server_id: int):
    """Toggle server active status"""
    db = SessionLocal()
    try:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        server.is_active = not server.is_active
        server.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(server)
        
        # Broadcast status change
        status = "activated" if server.is_active else "deactivated"
        await manager.broadcast(f"Server {status}: {server.name}", "server_status_changed")
        
        return {
            "id": server.id,
            "name": server.name,
            "ip": server.ip,
            "port": server.port,
            "user": server.user,
            "status": "active" if server.is_active else "inactive",
            "created_at": server.created_at,
            "updated_at": server.updated_at
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# Alert Service Endpoints
class AlertConditionCreate(BaseModel):
    name: str
    server_id: int
    metric_type: str
    field: str
    comparison: str
    threshold_value: float
    severity: str = "medium"
    cooldown_minutes: int = 10
    notification_emails: Optional[str] = None
    is_active: bool = True

@app.post("/alerts/", response_model=dict)
async def create_alert_condition(alert_data: AlertConditionCreate):
    """Create a new alert condition"""
    success = alert_service.create_alert_condition(
        name=alert_data.name,
        server_id=alert_data.server_id,
        metric_type=alert_data.metric_type,
        field=alert_data.field,
        comparison=alert_data.comparison,
        threshold_value=alert_data.threshold_value,
        severity=alert_data.severity,
        cooldown_minutes=alert_data.cooldown_minutes,
        notification_emails=alert_data.notification_emails,
        is_active=alert_data.is_active
    )
    
    if success:
        await manager.broadcast(f"New alert condition created: {alert_data.name}", "alert_created")
        return {"message": "Alert condition created successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to create alert condition")

@app.get("/alerts/", response_model=List[dict])
async def get_alert_conditions():
    """Get all active alert conditions"""
    alerts = alert_service.get_active_alerts()
    
    return [{
        "id": alert.id,
        "name": alert.name,
        "server_id": alert.server_id,
        "metric_type": alert.metric_type,
        "field": alert.field,
        "comparison": alert.comparison,
        "threshold_value": alert.threshold_value,
        "severity": alert.severity,
        "cooldown_minutes": alert.cooldown_minutes,
        "is_active": alert.is_active
    } for alert in alerts]

@app.get("/alerts/history/", response_model=List[dict])
async def get_alert_history(limit: int = 100):
    """Get alert history"""
    history = alert_service.get_alert_history(limit)
    
    return [{
        "id": item.id,
        "alert_id": item.alert_id,
        "server_id": item.server_id,
        "message": item.message,
        "severity": item.severity,
        "triggered_at": item.triggered_at,
        "resolved": item.resolved,
        "resolved_at": item.resolved_at
    } for item in history]

@app.post("/alerts/{alert_id}/resolve", response_model=dict)
async def resolve_alert(alert_id: int):
    """Mark an alert as resolved"""
    success = alert_service.mark_alert_resolved(alert_id)
    
    if success:
        await manager.broadcast(f"Alert {alert_id} marked as resolved", "alert_resolved")
        return {"message": "Alert marked as resolved"}
    else:
        raise HTTPException(status_code=404, detail="Alert not found")

# Log Service Endpoints
class LogSourceCreate(BaseModel):
    server_id: int
    name: str
    file_path: str
    format: str = "auto"
    error_pattern: Optional[str] = None
    warning_pattern: Optional[str] = None
    custom_patterns: Optional[dict] = None
    is_active: bool = True

@app.post("/logs/sources/", response_model=dict)
async def create_log_source(log_source: LogSourceCreate):
    """Create a new log source"""
    custom_patterns_dict = log_source.custom_patterns or {}
    
    success = log_service.create_log_source(
        server_id=log_source.server_id,
        name=log_source.name,
        file_path=log_source.file_path,
        format=log_source.format,
        error_pattern=log_source.error_pattern,
        warning_pattern=log_source.warning_pattern,
        custom_patterns=custom_patterns_dict,
        is_active=log_source.is_active
    )
    
    if success:
        await manager.broadcast(f"New log source created: {log_source.name}", "log_source_created")
        return {"message": "Log source created successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to create log source")

@app.get("/logs/sources/", response_model=List[dict])
async def get_log_sources():
    """Get all log sources"""
    sources = log_service.get_log_sources()
    
    return [{
        "id": source.id,
        "server_id": source.server_id,
        "name": source.name,
        "file_path": source.file_path,
        "format": source.format,
        "is_active": source.is_active
    } for source in sources]

@app.get("/logs/analyze/{server_id}", response_model=dict)
async def analyze_logs(server_id: int):
    """Analyze logs for a specific server"""
    results = log_service.analyze_logs(server_id)
    
    # Save results to database
    log_service.save_log_results(server_id, results)
    
    return results

@app.get("/logs/recent/{log_source_id}", response_model=List[dict])
async def get_recent_logs(log_source_id: int, limit: int = 50):
    """Get recent log entries from a specific log source"""
    return log_service.get_recent_log_entries(log_source_id, limit)

# Monitoring endpoints
@app.post("/servers/{server_id}/monitor/start")
async def start_monitoring_server(server_id: int):
    """Start monitoring a specific server"""
    monitoring_service.add_server_to_monitoring(server_id)
    await manager.broadcast(json.dumps({
        "type": "monitoring_started",
        "server_id": server_id,
        "message": f"Started monitoring server {server_id}",
        "timestamp": datetime.utcnow().isoformat()
    }), "monitoring_started")
    return {"message": "Server monitoring started"}

@app.post("/servers/{server_id}/monitor/stop")
async def stop_monitoring_server(server_id: int):
    """Stop monitoring a specific server"""
    monitoring_service.remove_server_from_monitoring(server_id)
    await manager.broadcast(f"Stopped monitoring server {server_id}", "monitoring_stopped")
    return {"message": "Server monitoring stopped"}

@app.get("/servers/{server_id}/metrics", response_model=dict)
async def get_server_metrics(server_id: int):
    """Get current metrics for a server"""
    # Connect to server and get metrics
    db = SessionLocal()
    try:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Get a fresh connection to the server
        if server_id not in ssh_service.clients:
            use_key = server.ssh_key_path is not None
            success, message = ssh_service.connect(
                server_id=server_id,
                hostname=server.ip,
                port=server.port,
                username=server.user,
                password=server.password_encrypted if not use_key else None,
                key_path=server.ssh_key_path if use_key else None
            )
            
            if not success:
                raise HTTPException(status_code=500, detail=f"Failed to connect: {message}")
        
        # Get metrics
        metrics = ssh_service.get_metrics(server_id)
        if not metrics:
            raise HTTPException(status_code=500, detail="Failed to get metrics")
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# Real-time status endpoints
@app.get("/status/realtime")
async def get_realtime_status():
    """Get real-time status of all servers"""
    statuses = monitoring_service.get_all_server_statuses()
    return {
        "server_statuses": statuses,
        "websocket_connections": manager.get_connection_count(),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/status/server/{server_id}")
async def get_server_realtime_status(server_id: int):
    """Get real-time status of a specific server"""
    status = monitoring_service.get_server_status(server_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Server not found or not monitored")
    
    return {
        "server_id": server_id,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)