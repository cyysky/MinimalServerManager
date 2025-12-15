import React, { useState, useEffect } from 'react';
import websocketService from '../utils/websocketService';

const WebSocketTest = () => {
  const [status, setStatus] = useState('disconnected');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [connectionInfo, setConnectionInfo] = useState({});

  useEffect(() => {
    // Set up message handlers
    const handleConnected = (data) => {
      setStatus('connected');
      addMessage('System', 'WebSocket connected successfully');
    };

    const handleDisconnected = (data) => {
      setStatus('disconnected');
      addMessage('System', `WebSocket disconnected: ${data.reason}`);
    };

    const handleMessage = (message) => {
      addMessage('Server', JSON.stringify(message, null, 2));
    };

    const handlePong = (message) => {
      addMessage('Server', `Pong received: ${message.timestamp}`);
    };

    const handleError = (error) => {
      addMessage('Error', error.error || 'Unknown error');
    };

    // Register handlers
    websocketService.onMessage('connected', handleConnected);
    websocketService.onMessage('disconnected', handleDisconnected);
    websocketService.onMessage('message', handleMessage);
    websocketService.onMessage('pong', handlePong);
    websocketService.onMessage('error', handleError);

    // Connect to WebSocket
    websocketService.connect();

    // Set up interval for status updates
    const statusInterval = setInterval(() => {
      setConnectionInfo(websocketService.getStatus());
    }, 1000);

    return () => {
      // Clean up
      websocketService.offMessage('connected', handleConnected);
      websocketService.offMessage('disconnected', handleDisconnected);
      websocketService.offMessage('message', handleMessage);
      websocketService.offMessage('pong', handlePong);
      websocketService.offMessage('error', handleError);
      clearInterval(statusInterval);
      websocketService.disconnect();
    };
  }, []);

  const addMessage = (sender, message) => {
    setMessages(prev => [...prev, { sender, message, timestamp: new Date().toISOString() }]);
  };

  const sendMessage = () => {
    if (!inputMessage.trim()) return;

    const message = {
      type: 'custom',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    if (websocketService.sendMessage(message)) {
      addMessage('Client', inputMessage);
      setInputMessage('');
    } else {
      addMessage('System', 'Failed to send message - WebSocket not connected');
    }
  };

  const sendPing = () => {
    if (websocketService.ping()) {
      addMessage('Client', 'Ping sent');
    } else {
      addMessage('System', 'Failed to send ping - WebSocket not connected');
    }
  };

  return (
    <div className="websocket-test-container">
      <h2>WebSocket Test</h2>
      <div className="status-bar">
        <span className={`status-indicator ${status}`}>{status}</span>
        <div className="connection-info">
          <span>Attempts: {connectionInfo.reconnectAttempts || 0}/{connectionInfo.maxReconnectAttempts || 0}</span>
        </div>
      </div>

      <div className="controls">
        <button onClick={sendPing} disabled={status !== 'connected'}>
          Send Ping
        </button>
        <div className="message-input">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Type a message..."
            disabled={status !== 'connected'}
          />
          <button onClick={sendMessage} disabled={status !== 'connected' || !inputMessage.trim()}>
            Send
          </button>
        </div>
      </div>

      <div className="message-log">
        <h3>Message Log</h3>
        <div className="messages">
          {messages.length === 0 ? (
            <p className="no-messages">No messages yet</p>
          ) : (
            messages.map((msg, index) => (
              <div key={index} className={`message ${msg.sender.toLowerCase()}`}>
                <div className="message-header">
                  <span className="sender">{msg.sender}</span>
                  <span className="timestamp">{new Date(msg.timestamp).toLocaleTimeString()}</span>
                </div>
                <div className="message-content">
                  <pre>{msg.message}</pre>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <style jsx>{`
        .websocket-test-container {
          max-width: 800px;
          margin: 0 auto;
          padding: 20px;
          font-family: Arial, sans-serif;
        }

        .status-bar {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 20px;
          padding: 10px;
          background-color: #f5f5f5;
          border-radius: 5px;
        }

        .status-indicator {
          padding: 5px 10px;
          border-radius: 15px;
          font-weight: bold;
          font-size: 12px;
        }

        .status-indicator.connected {
          background-color: #4CAF50;
          color: white;
        }

        .status-indicator.disconnected {
          background-color: #F44336;
          color: white;
        }

        .connection-info {
          font-size: 12px;
          color: #666;
        }

        .controls {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
        }

        button {
          padding: 8px 16px;
          background-color: #4CAF50;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }

        button:disabled {
          background-color: #cccccc;
          cursor: not-allowed;
        }

        .message-input {
          display: flex;
          gap: 5px;
          flex-grow: 1;
        }

        input {
          flex-grow: 1;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
        }

        .message-log {
          border: 1px solid #ddd;
          border-radius: 5px;
          padding: 15px;
          max-height: 400px;
          overflow-y: auto;
        }

        .messages {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .message {
          padding: 10px;
          border-radius: 5px;
          border-left: 3px solid #ddd;
        }

        .message.system {
          border-left-color: #666;
          background-color: #f9f9f9;
        }

        .message.client {
          border-left-color: #4CAF50;
          background-color: #f0fff0;
          margin-left: 20px;
        }

        .message.server {
          border-left-color: #2196F3;
          background-color: #f0f7ff;
          margin-left: 40px;
        }

        .message.error {
          border-left-color: #F44336;
          background-color: #fff0f0;
        }

        .message-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 5px;
          font-size: 12px;
          color: #666;
        }

        .message-content {
          font-size: 14px;
        }

        .message-content pre {
          margin: 0;
          white-space: pre-wrap;
          word-wrap: break-word;
        }

        .no-messages {
          color: #999;
          text-align: center;
          padding: 20px;
        }
      `}</style>
    </div>
  );
};

export default WebSocketTest;