# Minimal Server Manager - Hardware Detection Service
# Detects server hardware and operating system information

import platform
import psutil
import socket
import re
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import subprocess

class HardwareDetector:
    """
    Service for detecting local server hardware and system information
    Used for gathering information about the host system
    """
    
    def __init__(self):
        self.logger = logging.getLogger('HardwareDetector')
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get comprehensive system information
        Returns dictionary with hardware and OS details
        """
        info = {
            'os': self._get_os_info(),
            'cpu': self._get_cpu_info(),
            'memory': self._get_memory_info(),
            'disks': self._get_disk_info(),
            'network': self._get_network_info(),
            'system': self._get_system_details()
        }
        return info
    
    def _get_os_info(self) -> Dict[str, str]:
        """Get operating system information"""
        try:
            return {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'architecture': platform.architecture()[0],
                'hostname': socket.gethostname(),
                'kernel': platform.uname().version,
                'distribution': self._get_distribution_info()
            }
        except Exception as e:
            self.logger.error(f"Error getting OS info: {e}")
            return {}
    
    def _get_distribution_info(self) -> Optional[str]:
        """Get Linux distribution info if applicable"""
        try:
            if platform.system() == 'Linux':
                # Try lsb_release first
                try:
                    result = subprocess.run(['lsb_release', '-d'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        match = re.search(r'Description:\s*(.+)', result.stdout)
                        if match:
                            return match.group(1).strip()
                except:
                    pass
                
                # Try /etc/os-release
                try:
                    with open('/etc/os-release', 'r') as f:
                        lines = f.readlines()
                        for line in lines:
                            if line.startswith('PRETTY_NAME='):
                                return line.split('=', 1)[1].strip().strip('"')
                except:
                    pass
            return None
        except Exception as e:
            self.logger.error(f"Error getting distribution info: {e}")
            return None
    
    def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information"""
        try:
            cpu_freq = psutil.cpu_freq()
            return {
                'physical_cores': psutil.cpu_count(logical=False),
                'logical_cores': psutil.cpu_count(logical=True),
                'max_frequency': cpu_freq.max if cpu_freq else None,
                'current_frequency': cpu_freq.current if cpu_freq else None,
                'brand': self._get_cpu_brand(),
                'usage': psutil.cpu_percent(interval=1, percpu=True)
            }
        except Exception as e:
            self.logger.error(f"Error getting CPU info: {e}")
            return {}
    
    def _get_cpu_brand(self) -> Optional[str]:
        """Get CPU brand/model"""
        try:
            if platform.system() == 'Windows':
                try:
                    import wmi
                    c = wmi.WMI()
                    for processor in c.Win32_Processor():
                        return processor.Name
                except ImportError:
                    # wmi module not available, try alternative method
                    try:
                        import winreg
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                           r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                        return winreg.QueryValueEx(key, "ProcessorNameString")[0]
                    except:
                        return "Unknown Windows CPU"
            else:
                # Linux/Mac
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        lines = f.readlines()
                        for line in lines:
                            if 'model name' in line:
                                return line.split(':', 1)[1].strip()
                except:
                    return "Unknown CPU"
            return None
        except Exception as e:
            self.logger.error(f"Error getting CPU brand: {e}")
            return None
    
    def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory information"""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                'total_memory_mb': round(mem.total / (1024 * 1024), 2),
                'available_memory_mb': round(mem.available / (1024 * 1024), 2),
                'used_memory_mb': round(mem.used / (1024 * 1024), 2),
                'memory_percentage': mem.percent,
                'total_swap_mb': round(swap.total / (1024 * 1024), 2) if swap.total else 0,
                'used_swap_mb': round(swap.used / (1024 * 1024), 2) if swap.used else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting memory info: {e}")
            return {}
    
    def _get_disk_info(self) -> List[Dict[str, Any]]:
        """Get disk information"""
        try:
            disks = []
            for partition in psutil.disk_partitions(all=False):
                if partition.fstype and partition.mountpoint:
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disks.append({
                            'device': partition.device,
                            'mount_point': partition.mountpoint,
                            'file_system': partition.fstype,
                            'total_gb': round(usage.total / (1024 * 1024 * 1024), 2),
                            'used_gb': round(usage.used / (1024 * 1024 * 1024), 2),
                            'free_gb': round(usage.free / (1024 * 1024 * 1024), 2),
                            'usage_percentage': usage.percent
                        })
                    except Exception as e:
                        self.logger.warning(f"Error getting disk usage for {partition.mountpoint}: {e}")
            return disks
        except Exception as e:
            self.logger.error(f"Error getting disk info: {e}")
            return []
    
    def _get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        try:
            net_io = psutil.net_io_counters()
            interfaces = psutil.net_if_addrs()
            
            interface_details = {}
            for interface, addrs in interfaces.items():
                ips = []
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ips.append({
                            'ip': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': addr.broadcast
                        })
                    elif addr.family == socket.AF_INET6:
                        ips.append({
                            'ip': addr.address,
                            'prefixlen': addr.netmask if hasattr(addr, 'netmask') else None
                        })
                
                if ips:
                    interface_details[interface] = ips
            
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_received': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_received': net_io.packets_recv,
                'interfaces': interface_details
            }
        except Exception as e:
            self.logger.error(f"Error getting network info: {e}")
            return {}
    
    def _get_system_details(self) -> Dict[str, Any]:
        """Get additional system details"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            return {
                'boot_time': datetime.fromtimestamp(boot_time).strftime('%Y-%m-%d %H:%M:%S'),
                'uptime': self._format_uptime(uptime_seconds),
                'uptime_seconds': uptime_seconds,
                'current_users': len(psutil.users()),
                'users': [user.name for user in psutil.users()]
            }
        except Exception as e:
            self.logger.error(f"Error getting system details: {e}")
            return {}
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{days}d {hours}h {minutes}m"
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage"""
        mem = psutil.virtual_memory()
        return {
            'total': mem.percent,
            'used_mb': round(mem.used / (1024 * 1024), 2),
            'free_mb': round(mem.available / (1024 * 1024), 2)
        }
    
    def check_disk_space(self, threshold: float = 90.0) -> List[Dict[str, Any]]:
        """Check disks for low space and return alarms"""
        alarms = []
        for partition in psutil.disk_partitions(all=False):
            if partition.fstype and partition.mountpoint:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    if usage.percent >= threshold:
                        alarms.append({
                            'device': partition.device,
                            'mount_point': partition.mountpoint,
                            'usage_percentage': usage.percent,
                            'free_mb': round(usage.free / (1024 * 1024), 2)
                        })
                except Exception as e:
                    self.logger.warning(f"Error checking disk {partition.mountpoint}: {e}")
        return alarms

# Singleton instance
hardware_detector = HardwareDetector()