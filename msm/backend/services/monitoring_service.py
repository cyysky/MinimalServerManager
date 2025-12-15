# Minimal Server Manager - Monitoring Service
# Handles real-time monitoring of servers and metrics

import threading
import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Server, ServerSpec, Metric, CustomCommand
from models import CustomCommand as Command
from services.ssh_service import ssh_service

class MonitoringService:
    """
    Service for real-time server monitoring
    Collects and stores performance metrics regularly
    """
    
    def __init__(self, database_url: str, websocket_manager=None):
        self.logger = logging.getLogger('MonitoringService')
        self.database_url = database_url
        self.running = False
        self.websocket_manager = websocket_manager
        
        # Create database engine and session
        self.engine = create_engine(database_url, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.Session = SessionLocal
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Monitoring intervals and settings
        self.monitoring_interval = 30  # Reduced to 30 seconds for better responsiveness
        self.status_check_interval = 10  # Quick status checks every 10 seconds
        self.active_servers = {}  # server_id: last_monitoring_time
        self.server_status_cache = {}  # server_id: current_status
        
    def start(self) -> None:
        """
        Start the monitoring service
        """
        if self.running:
            return
            
        self.running = True
        self.logger.info("Starting monitoring service...")
        
        # Start monitoring thread
        monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitoring_thread.start()
        
        # Start status check thread for immediate status updates
        status_thread = threading.Thread(target=self._status_check_loop, daemon=True)
        status_thread.start()
        
    def stop(self) -> None:
        """
        Stop the monitoring service
        """
        self.running = False
        self.logger.info("Monitoring service stopped")
    
    def add_server_to_monitoring(self, server_id: int) -> None:
        """
        Add a server to active monitoring
        """
        with self._lock:
            self.active_servers[server_id] = datetime.utcnow()
            self.logger.info(f"Added server {server_id} to monitoring")
            
        # Immediately check server status
        self._check_server_status_immediate(server_id)
    
    def remove_server_from_monitoring(self, server_id: int) -> None:
        """
        Remove a server from active monitoring
        """
        with self._lock:
            if server_id in self.active_servers:
                del self.active_servers[server_id]
            if server_id in self.server_status_cache:
                del self.server_status_cache[server_id]
            self.logger.info(f"Removed server {server_id} from monitoring")
    
    def _monitoring_loop(self) -> None:
        """
        Main monitoring loop that runs continuously
        """
        while self.running:
            try:
                self._monitor_all_servers()
                self._execute_custom_commands()
                
                # Sleep until next monitoring cycle
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)  # Wait longer if error occurs
    
    def _status_check_loop(self) -> None:
        """
        Quick status check loop for immediate status updates
        """
        while self.running:
            try:
                self._check_all_server_statuses()
                time.sleep(self.status_check_interval)
            except Exception as e:
                self.logger.error(f"Error in status check loop: {e}")
                time.sleep(5)
    
    def _check_all_server_statuses(self) -> None:
        """
        Check status of all active servers quickly
        """
        with self._lock:
            server_ids = list(self.active_servers.keys())
        
        if not server_ids:
            return
            
        for server_id in server_ids:
            try:
                self._check_server_status_immediate(server_id)
            except Exception as e:
                self.logger.error(f"Error checking status for server {server_id}: {e}")
    
    def _check_server_status_immediate(self, server_id: int) -> None:
        """
        Immediately check and update server status
        """
        db = self.Session()
        try:
            server = db.query(Server).filter(Server.id == server_id).first()
            if not server:
                return
                
            # Check connection status
            old_status = self.server_status_cache.get(server_id, 'unknown')
            new_status = 'offline'
            
            try:
                # Quick connection test
                if server_id in ssh_service.clients:
                    # Test with a simple command
                    success, _, _ = ssh_service.execute_command(server_id, "echo 'ping'")
                    if success:
                        new_status = 'online'
                else:
                    # Try to connect
                    use_key = server.use_key and server.ssh_key_path
                    success, message = ssh_service.connect(
                        server_id=server_id,
                        hostname=server.ip,
                        port=server.port,
                        username=server.user,
                        password=server.password_encrypted if not use_key else None,
                        key_path=server.ssh_key_path if use_key else None
                    )
                    if success:
                        new_status = 'online'
            except Exception as e:
                self.logger.debug(f"Status check failed for server {server_id}: {e}")
                new_status = 'offline'
            
            # Update status if changed
            if old_status != new_status:
                server.status = new_status
                server.last_connected = datetime.utcnow() if new_status == 'online' else server.last_connected
                db.commit()
                
                # Update cache
                with self._lock:
                    self.server_status_cache[server_id] = new_status
                
                # Broadcast status change via WebSocket
                if self.websocket_manager:
                    status_message = {
                        "type": "server_status_change",
                        "server_id": server_id,
                        "server_name": server.name,
                        "status": new_status,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    # Use a thread-safe approach for WebSocket broadcasting
                    self._broadcast_websocket_message(status_message, "status_update")
                
                self.logger.info(f"Server {server.name} status changed: {old_status} -> {new_status}")
                
        except Exception as e:
            self.logger.error(f"Error in immediate status check for server {server_id}: {e}")
        finally:
            db.close()
    
    def _monitor_all_servers(self) -> None:
        """
        Monitor all active servers
        """
        with self._lock:
            server_ids = list(self.active_servers.keys())
        
        if not server_ids:
            return
            
        self.logger.info(f"Monitoring {len(server_ids)} active servers...")
        
        db = self.Session()
        try:
            for server_id in server_ids:
                try:
                    self._monitor_server(server_id)
                except Exception as e:
                    self.logger.error(f"Error monitoring server {server_id}: {e}")
        finally:
            db.close()
    
    def _monitor_server(self, server_id: int) -> None:
        """
        Monitor a single server and store metrics
        """
        db = self.Session()
        try:
            server = db.query(Server).filter(Server.id == server_id).first()
            if not server:
                self.logger.warning(f"Server {server_id} not found")
                return
                
            # Connect to server if not already connected
            if server_id not in ssh_service.clients:
                self.logger.info(f"Connecting to server {server.name} ({server.ip}:{server.port})...")
                
                # Determine connection method
                use_key = server.use_key and server.ssh_key_path
                success, message = ssh_service.connect(
                    server_id=server_id,
                    hostname=server.ip,
                    port=server.port,
                    username=server.user,
                    password=server.password_encrypted if not use_key else None,
                    key_path=server.ssh_key_path if use_key else None
                )
                
                if not success:
                    self.logger.error(f"Failed to connect to server {server.name}: {message}")
                    # Update status to offline
                    if server.status != 'offline':
                        server.status = 'offline'
                        db.commit()
                        self._broadcast_status_change_async(server_id, server.name, 'offline')
                    return
                    
                self.logger.info(f"Connected to server {server.name}")
            
            # Get current server status
            success, stdout, stderr = ssh_service.execute_command(server_id, "uptime")
            
            # Update server status
            if success:
                if server.status != 'online':
                    server.status = "online"
                    server.last_connected = datetime.utcnow()
                    db.commit()
                    self._broadcast_status_change_async(server_id, server.name, 'online')
            else:
                if server.status != 'offline':
                    server.status = "offline"
                    db.commit()
                    self._broadcast_status_change_async(server_id, server.name, 'offline')
            
            # Get performance metrics
            metrics = ssh_service.get_metrics(server_id)
            if metrics:
                self._store_metrics(server_id, metrics)
                
                # Broadcast metrics via WebSocket
                if self.websocket_manager:
                    metrics_message = {
                        "type": "metrics_update",
                        "server_id": server_id,
                        "server_name": server.name,
                        "metrics": metrics,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    # Use a thread-safe approach for WebSocket broadcasting
                    self._broadcast_websocket_message(metrics_message, "metrics_update")
                
            # Get hardware info and update specs (less frequently)
            if (not server.specs or not server.specs.last_updated or
                (datetime.utcnow() - server.specs.last_updated).days >= 1):
                hardware_info = ssh_service.get_hardware_info(server_id)
                if hardware_info:
                    self._update_server_specs(server, hardware_info)
                    
        except Exception as e:
            self.logger.error(f"Error monitoring server {server_id}: {e}")
        finally:
            db.close()
    
    def _broadcast_websocket_message(self, message_data: dict, subscription_type: str) -> None:
        """
        Thread-safe WebSocket broadcasting using asyncio.run() in a new event loop
        """
        if self.websocket_manager:
            try:
                import asyncio
                # Create a new event loop for this thread
                asyncio.run(self.websocket_manager.broadcast(json.dumps(message_data), subscription_type))
            except Exception as e:
                self.logger.error(f"Failed to broadcast WebSocket message: {e}")
    
    def _broadcast_status_change_async(self, server_id: int, server_name: str, status: str) -> None:
        """
        Broadcast server status change via WebSocket (async version)
        """
        if self.websocket_manager:
            status_message = {
                "type": "server_status_change",
                "server_id": server_id,
                "server_name": server_name,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
            self._broadcast_websocket_message(status_message, "status_update")
    
    def _broadcast_status_change(self, server_id: int, server_name: str, status: str) -> None:
        """
        Broadcast server status change via WebSocket (sync wrapper)
        """
        self._broadcast_status_change_async(server_id, server_name, status)
    
    def _store_metrics(self, server_id: int, metrics: Dict[str, Any]) -> None:
        """
        Store performance metrics in the database
        """
        db = self.Session()
        try:
            # Store CPU metrics
            if 'cpu_usage' in metrics:
                cpu_metric = Metric(
                    server_id=server_id,
                    metric_type='cpu',
                    value=json.dumps(metrics['cpu_usage']),
                    timestamp=datetime.utcnow()
                )
                db.add(cpu_metric)
                
            # Store memory metrics
            if 'memory_usage' in metrics:
                memory_metric = Metric(
                    server_id=server_id,
                    metric_type='memory',
                    value=json.dumps(metrics['memory_usage']),
                    timestamp=datetime.utcnow()
                )
                db.add(memory_metric)
                
            # Store disk metrics  
            if 'disk_usage' in metrics:
                for disk in metrics['disk_usage']:
                    disk_metric = Metric(
                        server_id=server_id,
                        metric_type=f"disk_{disk['mount_point'].replace('/', '_')}",
                        value=json.dumps(disk),
                        timestamp=datetime.utcnow()
                    )
                    db.add(disk_metric)
                    
            db.commit()
            self.logger.info(f"Stored metrics for server {server_id}")
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error storing metrics for server {server_id}: {e}")
        finally:
            db.close()
    
    def _update_server_specs(self, server: Server, hardware_info: Dict[str, Any]) -> None:
        """
        Update server hardware specifications
        """
        db = self.Session()
        try:
            if not server.specs:
                server.specs = ServerSpec()
                
            server.specs.cpu_model = hardware_info.get('cpu_model', '')
            server.specs.cpu_cores = hardware_info.get('cpu_cores', 0)
            server.specs.cpu_threads = hardware_info.get('cpu_threads', 0)
            server.specs.total_ram = hardware_info.get('total_ram', '')
            server.specs.disk_info = json.dumps(hardware_info.get('disks', []))
            server.specs.os_info = hardware_info.get('os_info', '')
            server.specs.last_updated = datetime.utcnow()
            
            db.commit()
            self.logger.info(f"Updated hardware specs for server {server.id}")
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error updating hardware specs for server {server.id}: {e}")
        finally:
            db.close()
    
    def _execute_custom_commands(self) -> None:
        """
        Execute custom commands for all servers that have them configured
        """
        db = self.Session()
        try:
            # Find all enabled custom commands
            commands = db.query(Command).filter(Command.enabled == True).all()
            
            for command in commands:
                try:
                    # Connect to the server if needed
                    if command.server_id not in ssh_service.clients:
                        server = db.query(Server).filter(Server.id == command.server_id).first()
                        if not server:
                            continue
                            
                        use_key = server.use_key and server.ssh_key_path
                        success, message = ssh_service.connect(
                            server_id=command.server_id,
                            hostname=server.ip,
                            port=server.port,
                            username=server.user,
                            password=server.password_encrypted if not use_key else None,
                            key_path=server.ssh_key_path if use_key else None
                        )
                        
                        if not success:
                            self.logger.error(f"Failed to connect to server {command.server_id} for command {command.id}")
                            continue
                    
                    # Execute the command
                    success, stdout, stderr = ssh_service.execute_command(command.server_id, command.command)
                    
                    if success:
                        self.logger.info(f"Command '{command.name}' completed successfully on server {command.server_id}")
                        
                        # Store the result
                        # TODO: Implement result storage
                        
                    else:
                        self.logger.error(f"Command '{command.name}' failed on server {command.server_id}: {stderr}")
                        
                except Exception as e:
                    self.logger.error(f"Error executing command {command.id}: {e}")
        finally:
            db.close()
    
    def get_server_status(self, server_id: int) -> Optional[str]:
        """
        Get current status of a specific server
        """
        with self._lock:
            return self.server_status_cache.get(server_id)
    
    def get_all_server_statuses(self) -> Dict[int, str]:
        """
        Get status of all monitored servers
        """
        with self._lock:
            return self.server_status_cache.copy()

# Singleton instance
monitoring_service = None

def init_monitoring_service(database_url: str, websocket_manager=None):
    global monitoring_service
    if monitoring_service is None:
        monitoring_service = MonitoringService(database_url, websocket_manager)
    return monitoring_service