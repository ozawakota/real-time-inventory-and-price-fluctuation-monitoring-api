import type { WebSocketMessage } from '../api/types';

interface WebSocketConfig {
  url: string;
  protocols?: string[];
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface WebSocketCallbacks {
  onMessage?: (data: WebSocketMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private callbacks: WebSocketCallbacks = {};
  private reconnectAttempts = 0;
  private isManualClose = false;
  private reconnectTimer: NodeJS.Timeout | null = null;

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 5,
      ...config,
    };
  }

  connect(callbacks: WebSocketCallbacks = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    this.callbacks = callbacks;
    this.isManualClose = false;

    try {
      this.ws = new WebSocket(this.config.url, this.config.protocols);
      
      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.callbacks.onOpen?.();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketMessage;
          this.callbacks.onMessage?.(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        if (!this.isManualClose) {
          this.handleReconnect();
        }
        this.callbacks.onClose?.();
      };

      this.ws.onerror = (error) => {
        this.callbacks.onError?.(error);
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.handleReconnect();
    }
  }

  private handleReconnect() {
    if (
      this.isManualClose || 
      this.reconnectAttempts >= (this.config.maxReconnectAttempts || 5)
    ) {
      return;
    }

    this.reconnectAttempts++;
    
    this.reconnectTimer = setTimeout(() => {
      this.connect(this.callbacks);
    }, this.config.reconnectInterval);
  }

  disconnect() {
    this.isManualClose = true;
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.reconnectAttempts = 0;
  }

  send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, unable to send message');
    }
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get connectionState() {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
        return 'closed';
      default:
        return 'unknown';
    }
  }
}

// シングルトンインスタンスの作成
let inventoryWsClient: WebSocketClient | null = null;
let priceWsClient: WebSocketClient | null = null;

export function getInventoryWebSocket() {
  if (!inventoryWsClient) {
    const baseUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    inventoryWsClient = new WebSocketClient({
      url: `${baseUrl}/ws/inventory`,
    });
  }
  return inventoryWsClient;
}

export function getPriceWebSocket() {
  if (!priceWsClient) {
    const baseUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    priceWsClient = new WebSocketClient({
      url: `${baseUrl}/ws/price`,
    });
  }
  return priceWsClient;
}