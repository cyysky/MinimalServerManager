#!/usr/bin/env python3
"""
Test script for API endpoints
"""
import requests
import json
import time

def test_api():
    """Test REST API endpoints"""
    base_url = "http://localhost:8001"
    
    try:
        # Test 1: Health check
        print("Testing health endpoint...")
        response = requests.get(f"{base_url}/health")
        print(f"Health: {response.status_code} - {response.json()}")
        
        # Test 2: Create server
        print("\nTesting server creation...")
        server_data = {
            "name": "Test Server",
            "ip": "127.0.0.1",
            "port": 22,
            "user": "testuser",
            "password": "testpass"
        }
        response = requests.post(f"{base_url}/servers/", json=server_data)
        print(f"Create server: {response.status_code}")
        if response.status_code == 200:
            server = response.json()
            server_id = server["id"]
            print(f"Server created with ID: {server_id}")
            
            # Test 3: Get server list
            print("\nTesting server list...")
            response = requests.get(f"{base_url}/servers/")
            print(f"Server list: {response.status_code} - {len(response.json())} servers")
            
            # Test 4: Get specific server
            print(f"\nTesting server detail for ID {server_id}...")
            response = requests.get(f"{base_url}/servers/{server_id}")
            print(f"Server detail: {response.status_code}")
            if response.status_code == 200:
                server_detail = response.json()
                print(f"Server: {server_detail['name']} at {server_detail['ip']}")
            
            # Test 5: Start monitoring
            print(f"\nTesting monitoring start for server {server_id}...")
            response = requests.post(f"{base_url}/servers/{server_id}/monitor/start")
            print(f"Start monitoring: {response.status_code}")
            
            # Test 6: Get real-time status
            print("\nTesting real-time status...")
            response = requests.get(f"{base_url}/status/realtime")
            print(f"Real-time status: {response.status_code}")
            if response.status_code == 200:
                status = response.json()
                print(f"WebSocket connections: {status['websocket_connections']}")
                print(f"Server statuses: {status['server_statuses']}")
            
            # Test 7: Create alert condition
            print("\nTesting alert creation...")
            alert_data = {
                "name": "High CPU Alert",
                "server_id": server_id,
                "metric_type": "cpu",
                "field": "usage_percent",
                "comparison": "greater_than",
                "threshold_value": 80.0,
                "severity": "high",
                "cooldown_minutes": 5
            }
            response = requests.post(f"{base_url}/alerts/", json=alert_data)
            print(f"Create alert: {response.status_code}")
            
            # Test 8: Get alerts
            print("\nTesting alert list...")
            response = requests.get(f"{base_url}/alerts/")
            print(f"Alert list: {response.status_code} - {len(response.json())} alerts")
            
            print("\nAll API tests completed!")
            
        else:
            print(f"Failed to create server: {response.text}")
            
    except Exception as e:
        print(f"API test failed: {e}")

if __name__ == "__main__":
    test_api()
