/**
 * WebSocket Real-time Connection Hook
 * 
 * Centralized WebSocket management for real-time inventory and price updates.
 * Handles connection state, message routing, and automatic reconnection.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { wsClient } from '../api/client';
import { useInventoryRealTimeUpdates } from './use-inventory';
import { usePriceRealTimeUpdates } from './use-price';
import { toast } from 'react-hot-toast';

interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  reconnectAttempts: number;
}

interface UseWebSocketOptions {
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

/**
 * Main WebSocket hook for real-time updates
 */
export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    autoConnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5,
    onConnect,
    onDisconnect,
    onError,
  } = options;

  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    reconnectAttempts: 0,
  });

  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const isManualDisconnect = useRef(false);

  // Get real-time update handlers
  const { handleInventoryUpdate } = useInventoryRealTimeUpdates();
  const { handlePriceUpdate } = usePriceRealTimeUpdates();

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback((data: any) => {
    try {
      // Route messages based on type
      if (data.type?.includes('inventory')) {
        handleInventoryUpdate(data);
      } else if (data.type?.includes('price')) {
        handlePriceUpdate(data);
      } else if (data.type === 'system_notification') {
        // Handle system-wide notifications
        toast(data.data?.message || 'システム通知', {
          icon: '🔔',
          duration: 5000,
        });
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
    }
  }, [handleInventoryUpdate, handlePriceUpdate]);

  /**
   * Handle WebSocket connection errors
   */
  const handleConnectionError = useCallback((error: Event) => {
    setState(prev => ({
      ...prev,
      error: '接続エラーが発生しました',
      isConnecting: false,
      isConnected: false,
    }));

    onError?.(error);

    // Attempt reconnection if not manually disconnected
    if (!isManualDisconnect.current && state.reconnectAttempts < maxReconnectAttempts) {
      setState(prev => ({
        ...prev,
        reconnectAttempts: prev.reconnectAttempts + 1,
      }));

      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, reconnectInterval);
    }
  }, [onError, state.reconnectAttempts, maxReconnectAttempts, reconnectInterval]);

  /**
   * Connect to WebSocket servers
   */
  const connect = useCallback(() => {
    if (state.isConnected || state.isConnecting) {
      return;
    }

    setState(prev => ({
      ...prev,
      isConnecting: true,
      error: null,
    }));

    isManualDisconnect.current = false;

    try {
      // Connect to inventory updates
      wsClient.connectToInventory(
        (data) => handleMessage(data),
        (error) => handleConnectionError(error)
      );

      // Connect to price updates
      wsClient.connectToPrice(
        (data) => handleMessage(data),
        (error) => handleConnectionError(error)
      );

      setState(prev => ({
        ...prev,
        isConnected: true,
        isConnecting: false,
        error: null,
        reconnectAttempts: 0,
      }));

      onConnect?.();
      
      // Show connection success message (only after reconnect)
      if (state.reconnectAttempts > 0) {
        toast.success('リアルタイム接続が復旧しました', {
          icon: '🔄',
        });
      }

    } catch (error) {
      setState(prev => ({
        ...prev,
        isConnecting: false,
        error: '接続に失敗しました',
      }));
    }
  }, [state.isConnected, state.isConnecting, state.reconnectAttempts, handleMessage, handleConnectionError, onConnect]);

  /**
   * Disconnect from WebSocket servers
   */
  const disconnect = useCallback(() => {
    isManualDisconnect.current = true;
    
    // Clear reconnection timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    wsClient.disconnect();

    setState({
      isConnected: false,
      isConnecting: false,
      error: null,
      reconnectAttempts: 0,
    });

    onDisconnect?.();
  }, [onDisconnect]);

  /**
   * Force reconnection
   */
  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(() => {
      setState(prev => ({ ...prev, reconnectAttempts: 0 }));
      connect();
    }, 1000);
  }, [disconnect, connect]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect]); // Only run on mount/unmount

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    ...state,
    connect,
    disconnect,
    reconnect,
  };
}

/**
 * Connection status indicator hook
 */
export function useConnectionStatus() {
  const { isConnected, isConnecting, error, reconnectAttempts } = useWebSocket();

  const status = isConnected 
    ? 'connected'
    : isConnecting 
      ? 'connecting'
      : error
        ? 'error'
        : 'disconnected';

  const statusText = {
    connected: 'リアルタイム接続中',
    connecting: '接続中...',
    error: `接続エラー (再試行: ${reconnectAttempts}回)`,
    disconnected: '未接続',
  }[status];

  const statusColor = {
    connected: 'text-green-600',
    connecting: 'text-yellow-600',
    error: 'text-red-600',
    disconnected: 'text-gray-600',
  }[status];

  return {
    status,
    statusText,
    statusColor,
    isConnected,
    isConnecting,
    error,
    reconnectAttempts,
  };
}

/**
 * Periodic connection health check
 */
export function useConnectionHealthCheck(interval = 30000) {
  const { isConnected, reconnect } = useWebSocket({ autoConnect: false });
  const lastPingRef = useRef<number>(Date.now());

  useEffect(() => {
    if (!isConnected) return;

    const healthCheck = setInterval(() => {
      const now = Date.now();
      const timeSinceLastPing = now - lastPingRef.current;

      // If no activity for more than 2x the interval, trigger reconnect
      if (timeSinceLastPing > interval * 2) {
        console.warn('WebSocket connection appears stale, reconnecting...');
        reconnect();
      }

      lastPingRef.current = now;
    }, interval);

    return () => {
      clearInterval(healthCheck);
    };
  }, [isConnected, interval, reconnect]);

  // Update ping timestamp when connection changes
  useEffect(() => {
    lastPingRef.current = Date.now();
  }, [isConnected]);
}