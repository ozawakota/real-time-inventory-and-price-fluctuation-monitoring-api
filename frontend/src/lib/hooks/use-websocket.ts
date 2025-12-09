/**
 * WebSocket Real-time Connection Hook
 * 
 * Centralized WebSocket management for real-time inventory and price updates.
 * Handles connection state, message routing, and automatic reconnection.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useInventoryRealTimeUpdates } from './use-inventory';
import { getInventoryWebSocket, getPriceWebSocket } from '../websocket/client';
import toast from 'react-hot-toast';
import type { WebSocketMessage } from '../api/types';

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
  const inventoryWsRef = useRef(getInventoryWebSocket());
  const priceWsRef = useRef(getPriceWebSocket());

  // Get real-time update handlers
  const { handleInventoryUpdate } = useInventoryRealTimeUpdates();

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback((data: WebSocketMessage) => {
    try {
      // Route messages based on type
      if (data.type?.includes('inventory')) {
        handleInventoryUpdate(data);
      } else if (data.type === 'price_change') {
        // Handle price changes
        toast.success(`価格変更: ${data.data?.inventory_item?.name}`, {
          icon: '💰',
          duration: 4000,
        });
      } else if (data.type === 'stock_alert') {
        // Handle stock alerts
        const alertData = data.data;
        toast.error(`在庫アラート: ${alertData?.inventory_item?.name} - ${alertData?.alert?.message}`, {
          icon: '⚠️',
          duration: 8000,
        });
      } else if (data.type === 'connection_status') {
        console.log('Connection status:', data);
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
    }
  }, [handleInventoryUpdate]);

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
      // Connect to inventory WebSocket
      inventoryWsRef.current.connect({
        onMessage: handleMessage,
        onOpen: () => {
          setState(prev => ({
            ...prev,
            isConnected: true,
            isConnecting: false,
            error: null,
            reconnectAttempts: 0,
          }));
          onConnect?.();
          
          if (state.reconnectAttempts > 0) {
            toast.success('リアルタイム接続が復旧しました', {
              icon: '🔄',
            });
          }
        },
        onClose: () => {
          if (!isManualDisconnect.current) {
            setState(prev => ({
              ...prev,
              isConnected: false,
              isConnecting: false,
            }));
          }
        },
        onError: (error) => {
          setState(prev => ({
            ...prev,
            error: '接続エラーが発生しました',
            isConnecting: false,
            isConnected: false,
            reconnectAttempts: prev.reconnectAttempts + 1,
          }));
          onError?.(error);
        },
      });

    } catch (error) {
      setState(prev => ({
        ...prev,
        isConnecting: false,
        error: '接続に失敗しました',
      }));
    }
  }, [state.isConnected, state.isConnecting, state.reconnectAttempts, handleMessage, onConnect, onError]);

  /**
   * Disconnect from WebSocket servers
   */
  const disconnect = useCallback(() => {
    isManualDisconnect.current = true;
    
    // Clear reconnection timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    inventoryWsRef.current.disconnect();
    priceWsRef.current.disconnect();

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