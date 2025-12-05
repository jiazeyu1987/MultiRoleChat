import { useState, useEffect, useCallback, useRef } from 'react';

interface WebSocketMessage {
  event: string;
  session_id?: number;
  data?: any;
  timestamp: string;
  [key: string]: any;
}

interface UseWebSocketOptions {
  sessionId?: number;
  url?: string;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
  enableLogging?: boolean;
  autoConnect?: boolean;
}

interface UseWebSocketReturn {
  connected: boolean;
  error: string | null;
  lastMessage: WebSocketMessage | null;
  connectionCount: number;
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  sendMessage: (message: any) => void;
  clearError: () => void;
  getConnectionStats: () => any;
}

/**
 * WebSocket Hook for real-time communication
 * Supports Server-Sent Events (SSE) and WebSocket protocols
 */
export const useWebSocket = ({
  sessionId,
  url,
  reconnectAttempts = 5,
  reconnectInterval = 3000,
  heartbeatInterval = 30000,
  enableLogging = false,
  autoConnect = true
}: UseWebSocketOptions = {}): UseWebSocketReturn => {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [connectionCount, setConnectionCount] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const connectionStartTimeRef = useRef<number>(0);

  // 日志记录
  const log = useCallback((message: string, ...args: any[]) => {
    if (enableLogging) {
      console.log(`[WebSocket] ${message}`, ...args);
    }
  }, [enableLogging]);

  // 清理连接
  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    setConnected(false);
    log('Connection cleaned up');
  }, [log]);

  // 处理连接错误
  const handleConnectionError = useCallback((error: Error | string) => {
    const errorMessage = typeof error === 'string' ? error : error.message;
    setError(errorMessage);
    log('Connection error:', errorMessage);

    // 尝试重连
    if (reconnectAttemptsRef.current < reconnectAttempts) {
      reconnectAttemptsRef.current++;
      log(`Reconnection attempt ${reconnectAttemptsRef.current}/${reconnectAttempts}`);

      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, reconnectInterval);
    } else {
      log('Max reconnection attempts reached');
      setError('Connection failed after maximum reconnection attempts');
    }
  }, [reconnectAttempts, reconnectInterval, log]);

  // 设置WebSocket连接
  const setupWebSocket = useCallback(() => {
    if (!url) return;

    try {
      log('Setting up WebSocket connection');
      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => {
        log('WebSocket connected');
        setConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        setConnectionCount(prev => prev + 1);
        connectionStartTimeRef.current = Date.now();

        // 发送连接消息
        if (sessionId) {
          socket.send(JSON.stringify({
            type: 'subscribe',
            session_id: sessionId,
            timestamp: new Date().toISOString()
          }));
        }
      };

      socket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          log('WebSocket message received:', message);
          setLastMessage(message);
        } catch (err) {
          log('Failed to parse WebSocket message:', err);
        }
      };

      socket.onclose = (event) => {
        log('WebSocket closed:', event.code, event.reason);
        setConnected(false);
        socketRef.current = null;

        // 如果不是正常关闭，尝试重连
        if (event.code !== 1000 && reconnectAttemptsRef.current < reconnectAttempts) {
          handleConnectionError(`WebSocket closed with code ${event.code}: ${event.reason}`);
        }
      };

      socket.onerror = (event) => {
        log('WebSocket error:', event);
        handleConnectionError('WebSocket connection error');
      };
    } catch (err) {
      handleConnectionError(err instanceof Error ? err : new Error('Failed to setup WebSocket'));
    }
  }, [url, sessionId, reconnectAttempts, handleConnectionError, log]);

  // 设置SSE连接
  const setupSSE = useCallback(() => {
    if (!sessionId && !url) return;

    try {
      const sseUrl = sessionId ? `/api/sessions/${sessionId}/live` : '/api/system/live';
      log('Setting up SSE connection to:', sseUrl);

      const eventSource = new EventSource(sseUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        log('SSE connection opened');
        setConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        setConnectionCount(prev => prev + 1);
        connectionStartTimeRef.current = Date.now();
      };

      eventSource.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          log('SSE message received:', message);
          setLastMessage(message);

          // 处理特定事件
          if (message.event === 'connected') {
            log('SSE connection confirmed');
          } else if (message.event === 'heartbeat') {
            // 心跳包，更新连接状态
            setConnected(true);
          }
        } catch (err) {
          log('Failed to parse SSE message:', err);
        }
      };

      eventSource.onerror = (event) => {
        log('SSE error:', event);
        handleConnectionError('SSE connection error');
      };
    } catch (err) {
      handleConnectionError(err instanceof Error ? err : new Error('Failed to setup SSE'));
    }
  }, [sessionId, url, handleConnectionError, log]);

  // 连接到服务器
  const connect = useCallback(() => {
    if (connected) {
      log('Already connected');
      return;
    }

    cleanup();
    log('Initiating connection');

    // 优先使用WebSocket，回退到SSE
    if (url && url.startsWith('ws://') || url?.startsWith('wss://')) {
      setupWebSocket();
    } else {
      setupSSE();
    }
  }, [connected, cleanup, log, setupWebSocket, setupSSE, url]);

  // 断开连接
  const disconnect = useCallback(() => {
    log('Disconnecting');
    cleanup();
    reconnectAttemptsRef.current = 0;
  }, [cleanup, log]);

  // 重新连接
  const reconnect = useCallback(() => {
    log('Manual reconnect initiated');
    reconnectAttemptsRef.current = 0;
    disconnect();
    setTimeout(connect, 1000);
  }, [disconnect, connect, log]);

  // 发送消息
  const sendMessage = useCallback((message: any) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      try {
        const messageWithTimestamp = {
          ...message,
          timestamp: new Date().toISOString()
        };
        socketRef.current.send(JSON.stringify(messageWithTimestamp));
        log('Message sent:', messageWithTimestamp);
      } catch (err) {
        log('Failed to send message:', err);
        setError('Failed to send message');
      }
    } else {
      log('Cannot send message: WebSocket not connected');
      setError('Cannot send message: not connected');
    }
  }, [log]);

  // 清除错误
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // 获取连接统计
  const getConnectionStats = useCallback(() => {
    const connectionDuration = connectionStartTimeRef.current
      ? Date.now() - connectionStartTimeRef.current
      : 0;

    return {
      connected,
      connectionCount,
      connectionDuration: connectionDuration,
      reconnectAttempts: reconnectAttemptsRef.current,
      maxReconnectAttempts: reconnectAttempts,
      connectionType: socketRef.current ? 'WebSocket' : (eventSourceRef.current ? 'SSE' : 'None'),
      lastMessageTime: lastMessage?.timestamp,
      error
    };
  }, [connected, connectionCount, lastMessage, error, reconnectAttempts]);

  // 设置心跳检测
  useEffect(() => {
    if (connected && heartbeatInterval > 0) {
      heartbeatIntervalRef.current = setInterval(() => {
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
          sendMessage({
            type: 'heartbeat',
            timestamp: new Date().toISOString()
          });
        }
      }, heartbeatInterval);
    } else {
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }
    }

    return () => {
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }
    };
  }, [connected, heartbeatInterval, sendMessage]);

  // 自动连接
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      cleanup();
    };
  }, [autoConnect, connect, cleanup]);

  // 页面卸载时清理
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  return {
    connected,
    error,
    lastMessage,
    connectionCount,
    connect,
    disconnect,
    reconnect,
    sendMessage,
    clearError,
    getConnectionStats
  };
};

// 辅型 hooks

/**
 * 使用系统级WebSocket连接
 */
export const useSystemWebSocket = (options: Omit<UseWebSocketOptions, 'sessionId'> = {}) => {
  return useWebSocket({
    url: '/api/system/live',
    ...options
  });
};

/**
 * 使用会话级WebSocket连接
 */
export const useSessionWebSocket = (sessionId: number, options: Omit<UseWebSocketOptions, 'sessionId'> = {}) => {
  return useWebSocket({
    sessionId,
    ...options
  });
};

/**
 * 使用实时统计WebSocket连接
 */
export const useRealtimeStats = (options: Omit<UseWebSocketOptions, 'sessionId'> = {}) => {
  const { lastMessage, ...websocketState } = useSystemWebSocket(options);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    if (lastMessage && lastMessage.event === 'system_status_updated') {
      setStats(lastMessage.data);
    }
  }, [lastMessage]);

  return {
    ...websocketState,
    stats,
    lastMessage
  };
};

/**
 * 使用测试WebSocket连接（用于开发和调试）
 */
export const useTestWebSocket = (options: Omit<UseWebSocketOptions, 'sessionId'> = {}) => {
  const { sendMessage, ...websocketState } = useWebSocket({
    url: '/api/realtime/test',
    ...options
  });

  const sendTestEvent = useCallback((eventType: string, data: any = {}) => {
    sendMessage({
      event_type: eventType,
      data,
      test: true
    });
  }, [sendMessage]);

  return {
    ...websocketState,
    sendTestEvent
  };
};

export default useWebSocket;