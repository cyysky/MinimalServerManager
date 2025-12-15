#!/usr/bin/env python3
"""
Debug CPU usage extraction
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.ssh_service import ssh_service

def debug_cpu_usage():
    """Debug CPU usage extraction"""
    print("Testing SSH connection to 192.168.50.173...")
    
    # Test credentials
    hostname = "192.168.50.173"
    port = 22
    username = "chong"
    password = "Admin1234"
    
    # Test connection
    success, message = ssh_service.connect(
        server_id=999,
        hostname=hostname,
        port=port,
        username=username,
        password=password
    )
    
    print(f"Connection result: {success}")
    print(f"Message: {message}")
    
    if success:
        print("\nTesting different CPU usage commands...")
        
        # Test different top commands
        commands = [
            "top -bn1 | grep 'Cpu(s)'",
            "top -bn1 | head -2",
            "top -bn1 | head -5",
            "mpstat 1 1",
            "cat /proc/stat | head -1",
            "uptime"
        ]
        
        for cmd in commands:
            print(f"\n--- Command: {cmd} ---")
            success, stdout, stderr = ssh_service.execute_command(999, cmd)
            print(f"Success: {success}")
            if stdout:
                print(f"Raw output:\n{repr(stdout)}")
                print(f"Formatted output:\n{stdout}")
            if stderr:
                print(f"Error: {stderr}")
        
        # Disconnect
        ssh_service.disconnect(999)
        print("\nDisconnected successfully")

if __name__ == "__main__":
    debug_cpu_usage()