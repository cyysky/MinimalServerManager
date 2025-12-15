#!/usr/bin/env python3
"""
Test SSH connectivity to the server
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.ssh_service import ssh_service

def test_ssh_connection():
    """Test SSH connection to the server"""
    print("Testing SSH connection to 192.168.50.173...")
    
    # Test credentials
    hostname = "192.168.50.173"
    port = 22
    username = "chong"
    password = "Admin1234"
    
    # Test connection
    success, message = ssh_service.connect(
        server_id=999,  # Use a test server ID
        hostname=hostname,
        port=port,
        username=username,
        password=password
    )
    
    print(f"Connection result: {success}")
    print(f"Message: {message}")
    
    if success:
        print("\nTesting hardware info retrieval...")
        hardware_info = ssh_service.get_hardware_info(999)
        if hardware_info:
            print("Hardware info retrieved successfully:")
            for key, value in hardware_info.items():
                print(f"  {key}: {value}")
        else:
            print("Failed to retrieve hardware info")
        
        print("\nTesting metrics retrieval...")
        metrics = ssh_service.get_metrics(999)
        if metrics:
            print("Metrics retrieved successfully:")
            for key, value in metrics.items():
                print(f"  {key}: {value}")
        else:
            print("Failed to retrieve metrics")
        
        # Test basic commands
        print("\nTesting basic commands...")
        commands = [
            "echo 'Test command'",
            "uname -a",
            "uptime",
            "lscpu | head -10",
            "free -h",
            "df -h | head -5"
        ]
        
        # Test nvtop availability
        print("\nTesting nvtop availability...")
        nvtop_success, nvtop_stdout, nvtop_stderr = ssh_service.execute_command(999, "which nvtop")
        print(f"nvtop check command: which nvtop")
        print(f"Success: {nvtop_success}")
        if nvtop_stdout:
            print(f"nvtop found at: {nvtop_stdout}")
        if nvtop_stderr:
            print(f"nvtop check error: {nvtop_stderr}")
        
        # Also try nvtop --version to see if it's actually functional
        if nvtop_success:
            print("\nTesting nvtop functionality...")
            version_success, version_stdout, version_stderr = ssh_service.execute_command(999, "nvtop --version")
            print(f"nvtop version command: nvtop --version")
            print(f"Success: {version_success}")
            if version_stdout:
                print(f"nvtop version: {version_stdout}")
            if version_stderr:
                print(f"nvtop version error: {version_stderr}")
        
        for cmd in commands:
            success, stdout, stderr = ssh_service.execute_command(999, cmd)
            print(f"\nCommand: {cmd}")
            print(f"Success: {success}")
            if stdout:
                print(f"Output: {stdout[:200]}...")
            if stderr:
                print(f"Error: {stderr}")
        
        # Disconnect
        ssh_service.disconnect(999)
        print("\nDisconnected successfully")
    else:
        print("Connection failed!")
        return False
    
    return True

if __name__ == "__main__":
    test_ssh_connection()