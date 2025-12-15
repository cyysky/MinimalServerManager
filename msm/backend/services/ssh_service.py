# Minimal Server Manager - SSH Service
# Handles SSH connections to remote servers

import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError
import socket
import re
import json
import threading
import time
from typing import Optional, Dict, Any, Tuple
import logging
from datetime import datetime

class SSHService:
    """
    Service for managing SSH connections to remote servers
    Handles authentication, command execution, and connection testing
    """
    
    def __init__(self):
        self.logger = logging.getLogger('SSHService')
        self._lock = threading.Lock()  # Thread safety lock
        self.clients = {}  # server_id: {'ssh': ssh_client, 'last_used': timestamp, 'connection_info': dict}
        self.connection_timeout = 300  # 5 minutes timeout for idle connections
        self.max_retries = 3
        self.retry_delay = 1  # seconds
    
    def connect(self, server_id: int, hostname: str, port: int, username: str,
                password: Optional[str] = None, key_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Establish SSH connection to a server with retry logic and thread safety
        Returns (success, message)
        """
        with self._lock:
            # Check if already connected and connection is still valid
            if server_id in self.clients:
                client_info = self.clients[server_id]
                ssh = client_info['ssh']
                
                # Test if connection is still alive
                try:
                    # Quick test command
                    stdin, stdout, stderr = ssh.exec_command("echo 'ping'")
                    stdout.read()  # Consume output
                    if stdout.channel.recv_exit_status() == 0:
                        # Update last used time
                        client_info['last_used'] = time.time()
                        return True, "Already connected"
                except:
                    # Connection is dead, remove it
                    self._remove_connection(server_id)
            
            # Try to connect with retries
            for attempt in range(self.max_retries):
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    # Connection timeout and keepalive settings
                    ssh.connect(
                        hostname,
                        port=port,
                        username=username,
                        password=password,
                        pkey=paramiko.RSAKey.from_private_key_file(key_path) if key_path else None,
                        timeout=10,
                        banner_timeout=10,
                        auth_timeout=10,
                        compress=False
                    )
                    
                    # Enable keepalive
                    ssh.get_transport().set_keepalive(30)
                    
                    # Store the active connection with metadata
                    self.clients[server_id] = {
                        'ssh': ssh,
                        'last_used': time.time(),
                        'connection_info': {
                            'hostname': hostname,
                            'port': port,
                            'username': username,
                            'connected_at': datetime.utcnow()
                        }
                    }
                    
                    self.logger.info(f"Connected to server {server_id} ({hostname}:{port})")
                    return True, "Connection successful"
                    
                except AuthenticationException as e:
                    if attempt == self.max_retries - 1:
                        return False, f"Authentication failed after {self.max_retries} attempts: {str(e)}"
                except NoValidConnectionsError as e:
                    if attempt == self.max_retries - 1:
                        return False, f"Connection error after {self.max_retries} attempts: {str(e)}"
                except SSHException as e:
                    if attempt == self.max_retries - 1:
                        return False, f"SSH error after {self.max_retries} attempts: {str(e)}"
                except socket.timeout:
                    if attempt == self.max_retries - 1:
                        return False, "Connection timed out after retries"
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        return False, f"Unexpected error after {self.max_retries} attempts: {str(e)}"
                
                # Wait before retry
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
            
            return False, "Failed to connect after all retries"
    
    def _remove_connection(self, server_id: int) -> None:
        """Remove a connection safely"""
        if server_id in self.clients:
            try:
                self.clients[server_id]['ssh'].close()
            except:
                pass
            finally:
                del self.clients[server_id]
                self.logger.info(f"Removed connection to server {server_id}")
    
    def cleanup_idle_connections(self) -> None:
        """Clean up idle connections that exceed timeout"""
        current_time = time.time()
        with self._lock:
            idle_servers = []
            for server_id, client_info in self.clients.items():
                if current_time - client_info['last_used'] > self.connection_timeout:
                    idle_servers.append(server_id)
            
            for server_id in idle_servers:
                self._remove_connection(server_id)
                self.logger.info(f"Cleaned up idle connection to server {server_id}")
    
    def execute_command(self, server_id: int, command: str) -> Tuple[bool, str, str]:
        """
        Execute a command on the connected server
        Returns (success, stdout, stderr)
        """
        if server_id not in self.clients:
            return False, "", "Not connected to server"
            
        try:
            ssh = self.clients[server_id]['ssh']
            stdin, stdout, stderr = ssh.exec_command(command)
            
            # Read output and error
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            
            self.logger.info(f"Executed command '{command}' on server {server_id}")
            return True, output, error
            
        except Exception as e:
            return False, "", str(e)
    
    def get_hardware_info(self, server_id: int) -> Optional[Dict[str, Any]]:
        """
        Gather hardware information from the server
        """
        if server_id not in self.clients:
            return None
            
        try:
            ssh = self.clients[server_id]['ssh']
            
            # Get hardware information
            hardware = {}
            
            # CPU info
            stdin, stdout, stderr = ssh.exec_command("lscpu")
            cpu_info = stdout.read().decode('utf-8')
            hardware['cpu_model'] = self._extract_cpu_model(cpu_info)
            hardware['cpu_cores'] = self._extract_cpu_cores(cpu_info)
            
            # RAM info
            stdin, stdout, stderr = ssh.exec_command("free -h")
            ram_info = stdout.read().decode('utf-8')
            hardware['total_ram'] = self._extract_ram_total(ram_info)
            
            # Disk info
            stdin, stdout, stderr = ssh.exec_command("df -h")
            disk_info = stdout.read().decode('utf-8')
            hardware['disks'] = self._extract_disks(disk_info)
            
            # OS info
            stdin, stdout, stderr = ssh.exec_command("uname -a")
            os_info = stdout.read().decode('utf-8').strip()
            hardware['os_info'] = os_info
            
            return hardware
            
        except Exception as e:
            self.logger.error(f"Error getting hardware info: {e}")
            return None
    
    def get_metrics(self, server_id: int) -> Optional[Dict[str, Any]]:
        """
        Get performance metrics from the server
        """
        if server_id not in self.clients:
            return None
            
        try:
            ssh = self.clients[server_id]['ssh']
            
            metrics = {}
            
            # CPU usage
            stdin, stdout, stderr = ssh.exec_command("top -bn1 | grep 'Cpu(s)'")
            cpu_output = stdout.read().decode('utf-8')
            cpu_usage = self._extract_cpu_usage(cpu_output)
            metrics['cpu_usage'] = cpu_usage
            
            # Memory usage
            stdin, stdout, stderr = ssh.exec_command("free -m")
            mem_output = stdout.read().decode('utf-8')
            mem_usage = self._extract_memory_usage(mem_output)
            metrics['memory_usage'] = mem_usage
            
            # Disk usage
            stdin, stdout, stderr = ssh.exec_command("df -h")
            disk_output = stdout.read().decode('utf-8')
            disk_usage = self._extract_disk_usage(disk_output)
            metrics['disk_usage'] = disk_usage
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting metrics: {e}")
            return None
    
    def disconnect(self, server_id: int) -> None:
        """
        Disconnect from the server
        """
        if server_id in self.clients:
            try:
                self.clients[server_id]['ssh'].close()
            except:
                pass
            finally:
                del self.clients[server_id]
                self.logger.info(f"Disconnected from server {server_id}")
    
    def close_all(self) -> None:
        """
        Close all active SSH connections
        """
        for server_id in list(self.clients.keys()):
            self.disconnect(server_id)
    
    # Helper methods for parsing command outputs
    
    def _extract_cpu_model(self, cpu_info: str) -> Optional[str]:
        """Extract CPU model from lscpu output"""
        match = re.search(r'Model name:\s*(.+)', cpu_info)
        return match.group(1).strip() if match else None
    
    def _extract_cpu_cores(self, cpu_info: str) -> Optional[int]:
        """Extract CPU cores from lscpu output"""
        match = re.search(r'Core\(s\) per socket:\s*(\d+)', cpu_info)
        return int(match.group(1)) if match else None
    
    def _extract_ram_total(self, ram_info: str) -> Optional[str]:
        """Extract total RAM from free -h output"""
        match = re.search(r'Mem:\s*(\S+)', ram_info)
        return match.group(1) if match else None
    
    def _extract_disks(self, disk_info: str) -> list:
        """Extract disk information from df -h output"""
        disks = []
        lines = disk_info.split('\n')[1:]  # Skip header
        for line in lines:
            parts = line.split()
            if len(parts) >= 6 and not line.startswith('/dev/loop'):
                devices = parts[0]
                size = parts[1]
                used = parts[2]
                avail = parts[3]
                use_percent = parts[4]
                mount_point = parts[5]
                
                disk_info = {
                    'device': devices,
                    'size': size,
                    'used': used,
                    'available': avail,
                    'use_percent': use_percent,
                    'mount_point': mount_point
                }
                disks.append(disk_info)
        return disks
    
    def _extract_cpu_usage(self, cpu_output: str) -> Optional[Dict]:
        """Extract CPU usage from top output"""
        # Handle the format: %Cpu(s):  0.7 us,  0.7 sy,  0.0 ni, 98.5 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
        match = re.search(r'%Cpu\(s\):\s*(\d+\.\d+)\s*us,\s*(\d+\.\d+)\s*sy,\s*(\d+\.\d+)\s*ni,\s*(\d+\.\d+)\s*id', cpu_output)
        if match:
            user = float(match.group(1))
            system = float(match.group(2))
            nice = float(match.group(3))
            idle = float(match.group(4))
            
            return {
                'user': user,
                'system': system,
                'nice': nice,
                'idle': idle,
                'totalUsage': user + system + nice
            }
        
        # Alternative pattern for different formats
        match = re.search(r'(\d+\.\d+)\s*us,\s*(\d+\.\d+)\s*sy,\s*(\d+\.\d+)\s*ni,\s*(\d+\.\d+)\s*id', cpu_output)
        if match:
            user = float(match.group(1))
            system = float(match.group(2))
            nice = float(match.group(3))
            idle = float(match.group(4))
            
            return {
                'user': user,
                'system': system,
                'nice': nice,
                'idle': idle,
                'totalUsage': user + system + nice
            }
        
        # Fallback: try to extract individual values
        user_match = re.search(r'(\d+\.\d+)\s*us', cpu_output)
        system_match = re.search(r'(\d+\.\d+)\s*sy', cpu_output)
        idle_match = re.search(r'(\d+\.\d+)\s*id', cpu_output)
        
        if user_match or system_match or idle_match:
            user = float(user_match.group(1)) if user_match else 0.0
            system = float(system_match.group(1)) if system_match else 0.0
            idle = float(idle_match.group(1)) if idle_match else 0.0
            
            return {
                'user': user,
                'system': system,
                'idle': idle,
                'totalUsage': user + system
            }
        
        return None
    
    def _extract_memory_usage(self, mem_output: str) -> Optional[Dict]:
        """Extract memory usage from free -m output"""
        lines = mem_output.split('\n')
        if len(lines) > 1:
            mem_line = lines[1].split()
            if len(mem_line) >= 3:
                total = int(mem_line[1])
                used = int(mem_line[2])
                return {
                    'total_mb': total,
                    'used_mb': used,
                    'usage_percent': (used / total) * 100 if total > 0 else 0
                }
        return None
    
    def _extract_disk_usage(self, disk_output: str) -> list:
        """Extract disk usage from df -h output"""
        lines = disk_output.split('\n')[1:]  # Skip header
        disk_usages = []
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 6 and not line.startswith('/dev/loop'):
                mount_point = parts[5]
                use_percent = parts[4].rstrip('%')
                
                disk_usage = {
                    'mount_point': mount_point,
                    'usage_percent': float(use_percent) if use_percent.replace('%', '').isdigit() else 0.0
                }
                disk_usages.append(disk_usage)
        return disk_usages

# Singleton instance
ssh_service = SSHService()