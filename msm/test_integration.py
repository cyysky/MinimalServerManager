#!/usr/bin/env python3
"""
Integration test script for end-to-end testing
"""
import requests
import asyncio
import websockets
import json
import time
import sqlite3
from concurrent.futures import ThreadPoolExecutor

class IntegrationTester:
    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.ws_uri = "ws://localhost:8001/ws"
        self.db_path = "data/app.db"
        self.test_results = []
        
    def log_test(self, test_name, status, details=""):
        """Log test results"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        status_symbol = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"{status_symbol} {test_name}: {status} {details}")
        
    def test_database_persistence(self):
        """Test database operations and persistence"""
        try:
            # Connect to database and check if test server exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if test server exists
            cursor.execute("SELECT * FROM servers WHERE name = 'Test Server'")
            server = cursor.fetchone()
            if server:
                self.log_test("Database Server Persistence", "PASS", f"Server ID: {server[0]}")
                
                # Check if alerts exist for this server
                cursor.execute("SELECT * FROM alerts WHERE server_id = ?", (server[0],))
                alerts = cursor.fetchall()
                self.log_test("Database Alert Persistence", "PASS", f"Found {len(alerts)} alerts")
            else:
                self.log_test("Database Server Persistence", "FAIL", "Test server not found")
                
            conn.close()
            return True
        except Exception as e:
            self.log_test("Database Persistence", "FAIL", str(e))
            return False
            
    def test_frontend_backend_communication(self):
        """Test API communication between frontend and backend"""
        try:
            # Test health endpoint
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Frontend-Backend Health Check", "PASS", f"Status: {data['status']}")
            else:
                self.log_test("Frontend-Backend Health Check", "FAIL", f"Status: {response.status_code}")
                return False
                
            # Test server list endpoint
            response = requests.get(f"{self.base_url}/servers/")
            if response.status_code == 200:
                servers = response.json()
                self.log_test("Frontend-Backend Server List", "PASS", f"Found {len(servers)} servers")
            else:
                self.log_test("Frontend-Backend Server List", "FAIL", f"Status: {response.status_code}")
                
            # Test alert list endpoint
            response = requests.get(f"{self.base_url}/alerts/")
            if response.status_code == 200:
                alerts = response.json()
                self.log_test("Frontend-Backend Alert List", "PASS", f"Found {len(alerts)} alerts")
            else:
                self.log_test("Frontend-Backend Alert List", "FAIL", f"Status: {response.status_code}")
                
            return True
        except Exception as e:
            self.log_test("Frontend-Backend Communication", "FAIL", str(e))
            return False
            
    async def test_realtime_updates(self):
        """Test real-time updates via WebSocket"""
        try:
            async with websockets.connect(self.ws_uri) as websocket:
                # Subscribe to updates
                subscribe_message = {
                    "type": "subscribe",
                    "subscriptions": ["server_status", "alerts"]
                }
                await websocket.send(json.dumps(subscribe_message))
                
                # Wait for subscription confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                sub_data = json.loads(response)
                
                if sub_data.get("type") == "subscribed":
                    self.log_test("WebSocket Subscription", "PASS", "Successfully subscribed to updates")
                else:
                    self.log_test("WebSocket Subscription", "FAIL", f"Unexpected response: {sub_data}")
                    return False
                    
                # Request current status
                status_message = {"type": "get_status"}
                await websocket.send(json.dumps(status_message))
                
                # Wait for status response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                status_data = json.loads(response)
                
                if status_data.get("type") == "server_statuses":
                    self.log_test("Real-time Status Updates", "PASS", f"Received status for servers: {list(status_data['data'].keys())}")
                else:
                    self.log_test("Real-time Status Updates", "FAIL", f"Unexpected status response: {status_data}")
                    
                return True
        except asyncio.TimeoutError:
            self.log_test("Real-time Updates", "FAIL", "Timeout waiting for WebSocket response")
            return False
        except Exception as e:
            self.log_test("Real-time Updates", "FAIL", str(e))
            return False
            
    def test_alert_workflow(self):
        """Test complete alert workflow"""
        try:
            # Create a test alert
            alert_data = {
                "name": "Integration Test Alert",
                "server_id": 2,  # Use existing test server
                "metric_type": "cpu",
                "field": "usage_percent",
                "comparison": "greater_than",
                "threshold_value": 90.0,
                "severity": "critical",
                "cooldown_minutes": 1
            }
            
            response = requests.post(f"{self.base_url}/alerts/", json=alert_data)
            if response.status_code == 200:
                alert = response.json()
                alert_id = alert["id"]
                self.log_test("Alert Creation", "PASS", f"Created alert ID: {alert_id}")
                
                # Test alert acknowledgment
                ack_response = requests.post(f"{self.base_url}/alerts/{alert_id}/acknowledge")
                if ack_response.status_code == 200:
                    self.log_test("Alert Acknowledgment", "PASS", "Alert acknowledged successfully")
                else:
                    self.log_test("Alert Acknowledgment", "FAIL", f"Status: {ack_response.status_code}")
                    
                # Test alert deletion
                delete_response = requests.delete(f"{self.base_url}/alerts/{alert_id}")
                if delete_response.status_code == 200:
                    self.log_test("Alert Deletion", "PASS", "Alert deleted successfully")
                else:
                    self.log_test("Alert Deletion", "FAIL", f"Status: {delete_response.status_code}")
                    
            else:
                self.log_test("Alert Creation", "FAIL", f"Status: {response.status_code}")
                
            return True
        except Exception as e:
            self.log_test("Alert Workflow", "FAIL", str(e))
            return False
            
    def test_error_handling(self):
        """Test error handling across the stack"""
        try:
            # Test invalid server ID
            response = requests.get(f"{self.base_url}/servers/99999")
            if response.status_code == 404:
                self.log_test("Error Handling - Invalid Server", "PASS", "Correctly returned 404")
            else:
                self.log_test("Error Handling - Invalid Server", "FAIL", f"Expected 404, got {response.status_code}")
                
            # Test invalid alert ID
            response = requests.get(f"{self.base_url}/alerts/99999")
            if response.status_code == 404:
                self.log_test("Error Handling - Invalid Alert", "PASS", "Correctly returned 404")
            else:
                self.log_test("Error Handling - Invalid Alert", "FAIL", f"Expected 404, got {response.status_code}")
                
            # Test invalid JSON
            response = requests.post(f"{self.base_url}/servers/", 
                                   json={"invalid": "data"}, 
                                   headers={"Content-Type": "application/json"})
            if response.status_code in [400, 422]:
                self.log_test("Error Handling - Invalid JSON", "PASS", f"Correctly returned {response.status_code}")
            else:
                self.log_test("Error Handling - Invalid JSON", "FAIL", f"Expected 400/422, got {response.status_code}")
                
            return True
        except Exception as e:
            self.log_test("Error Handling", "FAIL", str(e))
            return False
            
    def test_concurrent_operations(self):
        """Test concurrent operations"""
        def make_request(endpoint):
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                return response.status_code == 200
            except:
                return False
                
        try:
            # Test concurrent health checks
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request, "/health") for _ in range(10)]
                results = [future.result() for future in futures]
                
            if all(results):
                self.log_test("Concurrent Operations", "PASS", "All 10 concurrent requests succeeded")
            else:
                failed_count = results.count(False)
                self.log_test("Concurrent Operations", "FAIL", f"{failed_count}/10 requests failed")
                
            return True
        except Exception as e:
            self.log_test("Concurrent Operations", "FAIL", str(e))
            return False
            
    def run_all_tests(self):
        """Run all integration tests"""
        print("Starting Integration Tests...")
        print("=" * 50)
        
        # Test database persistence
        self.test_database_persistence()
        
        # Test frontend-backend communication
        self.test_frontend_backend_communication()
        
        # Test real-time updates
        asyncio.run(self.test_realtime_updates())
        
        # Test alert workflow
        self.test_alert_workflow()
        
        # Test error handling
        self.test_error_handling()
        
        # Test concurrent operations
        self.test_concurrent_operations()
        
        # Generate summary
        self.generate_summary()
        
    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "=" * 50)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 50)
        
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")
                    
        print("\nDetailed Results:")
        for result in self.test_results:
            status_symbol = "[PASS]" if result["status"] == "PASS" else "[FAIL]"
            print(f"  {status_symbol} {result['test']}: {result['status']}")

if __name__ == "__main__":
    tester = IntegrationTester()
    tester.run_all_tests()