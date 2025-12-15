#!/usr/bin/env python3
"""
Test script for WebSocket functionality
"""
import asyncio
import websockets
import json
import time

async def test_websocket():
    """Test WebSocket connection and messaging"""
    uri = "ws://localhost:8001/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected successfully")
            
            # Test 1: Send ping
            ping_message = {
                "type": "ping",
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(ping_message))
            print("Sent ping message")
            
            # Receive pong
            response = await websocket.recv()
            pong_data = json.loads(response)
            print(f"Received: {pong_data}")
            
            # Test 2: Subscribe to updates
            subscribe_message = {
                "type": "subscribe",
                "subscriptions": ["server_status", "alerts"]
            }
            await websocket.send(json.dumps(subscribe_message))
            print("Sent subscription message")
            
            # Receive subscription confirmation
            response = await websocket.recv()
            sub_data = json.loads(response)
            print(f"Received: {sub_data}")
            
            # Test 3: Request current status
            status_message = {
                "type": "get_status"
            }
            await websocket.send(json.dumps(status_message))
            print("Requested status")
            
            # Receive status
            response = await websocket.recv()
            status_data = json.loads(response)
            print(f"Received: {status_data}")
            
            print("\nAll WebSocket tests passed!")
            
    except Exception as e:
        print(f"WebSocket test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())