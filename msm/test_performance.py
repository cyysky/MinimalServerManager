#!/usr/bin/env python3
"""
Performance test script for load testing and performance evaluation
"""
import requests
import asyncio
import websockets
import json
import time
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

class PerformanceTester:
    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.ws_uri = "ws://localhost:8001/ws"
        self.results = {
            "api_performance": [],
            "websocket_performance": [],
            "memory_usage": [],
            "concurrent_connections": [],
            "errors": []
        }
        
    def measure_memory_usage(self):
        """Measure current memory usage"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss": memory_info.rss / 1024 / 1024,  # MB
                "vms": memory_info.vms / 1024 / 1024,  # MB
                "percent": process.memory_percent()
            }
        except:
            return {"rss": 0, "vms": 0, "percent": 0}
            
    def test_api_performance(self, num_requests=50, concurrent_users=5):
        """Test API performance under load"""
        print(f"Testing API performance with {num_requests} requests, {concurrent_users} concurrent users...")
        
        def make_request():
            start_time = time.time()
            try:
                response = requests.get(f"{self.base_url}/health")
                end_time = time.time()
                return {
                    "success": response.status_code == 200,
                    "response_time": (end_time - start_time) * 1000,  # ms
                    "status_code": response.status_code
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "success": False,
                    "response_time": (end_time - start_time) * 1000,
                    "error": str(e)
                }
                
        # Measure initial memory
        initial_memory = self.measure_memory_usage()
        
        # Execute concurrent requests
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in as_completed(futures)]
            
        total_time = time.time() - start_time
        
        # Measure final memory
        final_memory = self.measure_memory_usage()
        
        # Analyze results
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            performance_data = {
                "total_requests": num_requests,
                "successful_requests": len(successful_requests),
                "failed_requests": len(failed_requests),
                "success_rate": (len(successful_requests) / num_requests) * 100,
                "total_time": total_time,
                "requests_per_second": num_requests / total_time,
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_response_time": statistics.median(response_times),
                "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
                "memory_delta": final_memory["rss"] - initial_memory["rss"]
            }
        else:
            performance_data = {
                "total_requests": num_requests,
                "successful_requests": 0,
                "failed_requests": num_requests,
                "success_rate": 0,
                "error": "All requests failed"
            }
            
        self.results["api_performance"] = performance_data
        return performance_data
        
    async def test_websocket_performance(self, num_connections=10, test_duration=15):
        """Test WebSocket performance with multiple connections"""
        print(f"Testing WebSocket performance with {num_connections} connections for {test_duration} seconds...")
        
        connection_results = []
        connection_errors = []
        
        async def websocket_client(client_id):
            """Individual WebSocket client"""
            try:
                start_time = time.time()
                messages_sent = 0
                messages_received = 0
                
                async with websockets.connect(self.ws_uri) as websocket:
                    # Subscribe to updates
                    subscribe_message = {
                        "type": "subscribe",
                        "subscriptions": ["server_status", "alerts"]
                    }
                    await websocket.send(json.dumps(subscribe_message))
                    
                    # Wait for subscription confirmation
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        messages_received += 1
                    except:
                        pass
                    
                    # Send periodic messages during test duration
                    while time.time() - start_time < test_duration:
                        ping_message = {
                            "type": "ping",
                            "client_id": client_id,
                            "timestamp": time.time()
                        }
                        await websocket.send(json.dumps(ping_message))
                        messages_sent += 1
                        
                        # Receive response
                        try:
                            await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            messages_received += 1
                        except:
                            pass
                            
                        await asyncio.sleep(1)  # Send ping every second
                        
                end_time = time.time()
                connection_duration = end_time - start_time
                
                return {
                    "client_id": client_id,
                    "success": True,
                    "duration": connection_duration,
                    "messages_sent": messages_sent,
                    "messages_received": messages_received,
                    "messages_per_second": messages_sent / connection_duration
                }
                
            except Exception as e:
                return {
                    "client_id": client_id,
                    "success": False,
                    "error": str(e)
                }
                
        # Start all WebSocket connections
        start_time = time.time()
        tasks = [websocket_client(i) for i in range(num_connections)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_connections = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_connections = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exceptions = [r for r in results if not isinstance(r, dict)]
        
        if successful_connections:
            messages_per_second = [r["messages_per_second"] for r in successful_connections]
            performance_data = {
                "total_connections": num_connections,
                "successful_connections": len(successful_connections),
                "failed_connections": len(failed_connections),
                "exceptions": len(exceptions),
                "connection_success_rate": (len(successful_connections) / num_connections) * 100,
                "total_test_time": total_time,
                "avg_messages_per_second": statistics.mean(messages_per_second),
                "max_messages_per_second": max(messages_per_second),
                "min_messages_per_second": min(messages_per_second),
                "total_messages_sent": sum(r["messages_sent"] for r in successful_connections),
                "total_messages_received": sum(r["messages_received"] for r in successful_connections)
            }
        else:
            performance_data = {
                "total_connections": num_connections,
                "successful_connections": 0,
                "failed_connections": num_connections,
                "connection_success_rate": 0,
                "error": "All connections failed"
            }
            
        self.results["websocket_performance"] = performance_data
        return performance_data
        
    def test_memory_usage_over_time(self, duration=30):
        """Monitor memory usage over time"""
        print(f"Monitoring memory usage for {duration} seconds...")
        
        memory_samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            memory_info = self.measure_memory_usage()
            memory_samples.append({
                "timestamp": time.time() - start_time,
                "memory_mb": memory_info["rss"],
                "memory_percent": memory_info["percent"]
            })
            time.sleep(3)  # Sample every 3 seconds
            
        if memory_samples:
            memory_values = [s["memory_mb"] for s in memory_samples]
            self.results["memory_usage"] = {
                "samples": len(memory_samples),
                "duration": duration,
                "initial_memory_mb": memory_samples[0]["memory_mb"],
                "final_memory_mb": memory_samples[-1]["memory_mb"],
                "max_memory_mb": max(memory_values),
                "min_memory_mb": min(memory_values),
                "avg_memory_mb": statistics.mean(memory_values),
                "memory_growth_mb": memory_samples[-1]["memory_mb"] - memory_samples[0]["memory_mb"]
            }
            
        return self.results["memory_usage"]
        
    def test_concurrent_operations(self):
        """Test various concurrent operations"""
        print("Testing concurrent operations...")
        
        operations = [
            ("health_check", lambda: requests.get(f"{self.base_url}/health")),
            ("server_list", lambda: requests.get(f"{self.base_url}/servers/")),
            ("alert_list", lambda: requests.get(f"{self.base_url}/alerts/")),
            ("realtime_status", lambda: requests.get(f"{self.base_url}/status/realtime"))
        ]
        
        def run_operation(operation_name, operation_func):
            start_time = time.time()
            try:
                response = operation_func()
                end_time = time.time()
                return {
                    "operation": operation_name,
                    "success": response.status_code == 200,
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status_code
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "operation": operation_name,
                    "success": False,
                    "response_time": (end_time - start_time) * 1000,
                    "error": str(e)
                }
                
        # Test each operation with multiple concurrent requests
        concurrent_results = {}
        for op_name, op_func in operations:
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(run_operation, op_name, op_func) for _ in range(5)]
                results = [future.result() for future in as_completed(futures)]
                
            successful = [r for r in results if r["success"]]
            if successful:
                response_times = [r["response_time"] for r in successful]
                concurrent_results[op_name] = {
                    "total_requests": len(results),
                    "successful_requests": len(successful),
                    "success_rate": (len(successful) / len(results)) * 100,
                    "avg_response_time": statistics.mean(response_times),
                    "max_response_time": max(response_times)
                }
            else:
                concurrent_results[op_name] = {
                    "total_requests": len(results),
                    "successful_requests": 0,
                    "success_rate": 0,
                    "error": "All requests failed"
                }
                
        self.results["concurrent_connections"] = concurrent_results
        return concurrent_results
        
    def run_all_performance_tests(self):
        """Run all performance tests"""
        print("Starting Performance Tests...")
        print("=" * 60)
        
        # Test API performance
        api_results = self.test_api_performance()
        print(f"API Performance: {api_results['success_rate']:.1f}% success rate")
        
        # Test WebSocket performance
        ws_results = asyncio.run(self.test_websocket_performance())
        print(f"WebSocket Performance: {ws_results.get('connection_success_rate', 0):.1f}% connection success rate")
        
        # Test memory usage
        memory_results = self.test_memory_usage_over_time()
        print(f"Memory Usage: {memory_results.get('memory_growth_mb', 0):.1f}MB growth")
        
        # Test concurrent operations
        concurrent_results = self.test_concurrent_operations()
        print("Concurrent Operations Results:")
        for op, result in concurrent_results.items():
            print(f"  {op}: {result['success_rate']:.1f}% success rate")
            
        # Generate performance report
        self.generate_performance_report()
        
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        print("\n" + "=" * 60)
        print("PERFORMANCE TEST REPORT")
        print("=" * 60)
        
        # API Performance
        if self.results["api_performance"]:
            api = self.results["api_performance"]
            print(f"\nAPI Performance:")
            print(f"  Total Requests: {api['total_requests']}")
            print(f"  Success Rate: {api['success_rate']:.1f}%")
            print(f"  Requests/Second: {api['requests_per_second']:.1f}")
            print(f"  Avg Response Time: {api['avg_response_time']:.1f}ms")
            print(f"  P95 Response Time: {api['p95_response_time']:.1f}ms")
            print(f"  Memory Growth: {api['memory_delta']:.1f}MB")
            
        # WebSocket Performance
        if self.results["websocket_performance"]:
            ws = self.results["websocket_performance"]
            print(f"\nWebSocket Performance:")
            print(f"  Total Connections: {ws['total_connections']}")
            print(f"  Connection Success Rate: {ws['connection_success_rate']:.1f}%")
            print(f"  Avg Messages/Second: {ws['avg_messages_per_second']:.1f}")
            print(f"  Total Messages Sent: {ws['total_messages_sent']}")
            print(f"  Total Messages Received: {ws['total_messages_received']}")
            
        # Memory Usage
        if self.results["memory_usage"]:
            mem = self.results["memory_usage"]
            print(f"\nMemory Usage:")
            print(f"  Initial Memory: {mem['initial_memory_mb']:.1f}MB")
            print(f"  Final Memory: {mem['final_memory_mb']:.1f}MB")
            print(f"  Memory Growth: {mem['memory_growth_mb']:.1f}MB")
            print(f"  Max Memory: {mem['max_memory_mb']:.1f}MB")
            print(f"  Avg Memory: {mem['avg_memory_mb']:.1f}MB")
            
        # Concurrent Operations
        if self.results["concurrent_connections"]:
            print(f"\nConcurrent Operations:")
            for op, result in self.results["concurrent_connections"].items():
                print(f"  {op}:")
                print(f"    Success Rate: {result['success_rate']:.1f}%")
                print(f"    Avg Response Time: {result['avg_response_time']:.1f}ms")
                
        # Performance Summary
        print(f"\nPerformance Summary:")
        api_success = self.results["api_performance"].get("success_rate", 0)
        ws_success = self.results["websocket_performance"].get("connection_success_rate", 0)
        memory_growth = self.results["memory_usage"].get("memory_growth_mb", 0)
        
        if api_success >= 95 and ws_success >= 90 and memory_growth < 50:
            print("  Overall Performance: EXCELLENT")
        elif api_success >= 90 and ws_success >= 80 and memory_growth < 100:
            print("  Overall Performance: GOOD")
        elif api_success >= 80 and ws_success >= 70:
            print("  Overall Performance: ACCEPTABLE")
        else:
            print("  Overall Performance: NEEDS IMPROVEMENT")

if __name__ == "__main__":
    tester = PerformanceTester()
    tester.run_all_performance_tests()