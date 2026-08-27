import { useEffect, useRef, useState, useCallback } from "react";
import { WS_BASE_URL, WS_RECONNECT_BASE_MS, WS_RECONNECT_MAX_MS, WS_RECONNECT_JITTER, CONNECTION_STATUS } from "../config";
import { getToken } from "../services/api";

export function useRealtime(options = {}) {
  const {
    onMessage,
    sessionId,
    enabled = true,
    autoReconnect = true,
    onStatusChange,
  } = options;

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const [status, setStatus] = useState(CONNECTION_STATUS.DISCONNECTED);
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState(null);

  const updateStatus = useCallback((newStatus) => {
    setStatus(newStatus);
    onStatusChange?.(newStatus);
  }, [onStatusChange]);

  const connect = useCallback(() => {
    if (!enabled) return;
    
    const token = getToken();
    if (!token) {
      updateStatus(CONNECTION_STATUS.ERROR);
      setError("No authentication token available");
      return;
    }

    try {
      const wsUrl = sessionId 
        ? `${WS_BASE_URL}/ws/emergency/${sessionId}?token=${token}` 
        : `${WS_BASE_URL}/ws/live?token=${token}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        updateStatus(CONNECTION_STATUS.CONNECTED);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          setLastMessage(message);
          onMessage?.(message);
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      ws.onclose = (event) => {
        updateStatus(CONNECTION_STATUS.DISCONNECTED);
        wsRef.current = null;

        if (autoReconnect && enabled) {
          scheduleReconnect();
        }
      };

      ws.onerror = (err) => {
        updateStatus(CONNECTION_STATUS.ERROR);
        setError("WebSocket connection error");
        console.error("WebSocket error:", err);
      };

      updateStatus(CONNECTION_STATUS.CONNECTING);
    } catch (err) {
      updateStatus(CONNECTION_STATUS.ERROR);
      setError(err.message);
    }
  }, [enabled, onMessage, sessionId, updateStatus]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    const attempt = reconnectAttemptsRef.current;
    const baseDelay = WS_RECONNECT_BASE_MS * Math.pow(2, attempt);
    const jitter = baseDelay * WS_RECONNECT_JITTER * Math.random();
    const delay = Math.min(baseDelay + jitter, WS_RECONNECT_MAX_MS);

    reconnectAttemptsRef.current += 1;
    updateStatus(CONNECTION_STATUS.RECONNECTING);

    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, delay);
  }, [connect, updateStatus]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000, "Intentional disconnect");
      wsRef.current = null;
    }
    updateStatus(CONNECTION_STATUS.DISCONNECTED);
  }, [updateStatus]);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    status,
    lastMessage,
    error,
    connect,
    disconnect,
    send,
    isConnected: status === CONNECTION_STATUS.CONNECTED,
    isConnecting: status === CONNECTION_STATUS.CONNECTING || status === CONNECTION_STATUS.RECONNECTING,
  };
}
