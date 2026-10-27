'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  topic: string;
  data: any;
  timestamp?: string;
}

export function useSentinelWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [trafficStream, setTrafficStream] = useState<any[]>([]);
  const [alertStream, setAlertStream] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (typeof window === 'undefined') return;

    // Use current host or proxy
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//127.0.0.1:8000/api/v1/ws/live`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        // Subscribe to all primary topics
        ws.send(JSON.stringify({ action: 'subscribe', topic: 'traffic' }));
        ws.send(JSON.stringify({ action: 'subscribe', topic: 'alerts' }));
        ws.send(JSON.stringify({ action: 'subscribe', topic: 'metrics' }));
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setLastMessage(parsed);

          if (parsed.topic === 'traffic' && parsed.data) {
            setTrafficStream((prev) => [parsed.data, ...prev.slice(0, 19)]);
          } else if (parsed.topic === 'alerts' && parsed.data) {
            setAlertStream((prev) => [parsed.data, ...prev.slice(0, 9)]);
          }
        } catch {
          // ignore non-json ping/pong
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      };

      ws.onerror = () => {
        setIsConnected(false);
        ws.close();
      };
    } catch {
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  return {
    isConnected,
    lastMessage,
    trafficStream,
    alertStream,
  };
}
