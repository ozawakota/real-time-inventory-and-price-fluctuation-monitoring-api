// API型定義 - バックエンドAPIとの型安全な連携のため

export interface InventoryItem {
  id: number;
  name: string;
  sku: string;
  category: string;
  stock_quantity: number;
  reserved_quantity: number;
  min_stock_level: number;
  max_stock_level: number;
  unit_cost: number;
  selling_price: number;
  supplier: string;
  location: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  // 計算プロパティ
  available_quantity?: number;
  is_low_stock?: boolean;
}

export interface InventoryCreate {
  name: string;
  sku: string;
  category: string;
  stock_quantity: number;
  reserved_quantity?: number;
  min_stock_level: number;
  max_stock_level: number;
  unit_cost: number;
  selling_price: number;
  supplier: string;
  location: string;
  description?: string;
  is_active?: boolean;
}

export interface InventoryUpdate {
  name?: string;
  sku?: string;
  category?: string;
  stock_quantity?: number;
  reserved_quantity?: number;
  min_stock_level?: number;
  max_stock_level?: number;
  unit_cost?: number;
  selling_price?: number;
  supplier?: string;
  location?: string;
  description?: string;
  is_active?: boolean;
}

export interface PriceHistory {
  id: number;
  inventory_item_id: number;
  old_price: number;
  new_price: number;
  change_reason: string;
  changed_by: string;
  created_at: string;
  // リレーション
  inventory_item?: InventoryItem;
}

export interface PriceHistoryCreate {
  inventory_item_id: number;
  old_price: number;
  new_price: number;
  change_reason: string;
  changed_by: string;
}

export interface StockAlert {
  id: number;
  inventory_item_id: number;
  alert_type: 'LOW_STOCK' | 'OUT_OF_STOCK' | 'OVERSTOCK';
  message: string;
  threshold_value: number;
  current_value: number;
  is_resolved: boolean;
  created_at: string;
  resolved_at?: string;
  // リレーション
  inventory_item?: InventoryItem;
}

// API レスポンス型
export interface APIResponse<T> {
  data: T;
  message?: string;
  status: 'success' | 'error';
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// WebSocket メッセージ型
export interface WebSocketMessage {
  type: 'inventory_update' | 'price_change' | 'stock_alert' | 'connection_status';
  data: any;
  timestamp: string;
}

export interface InventoryUpdateMessage extends WebSocketMessage {
  type: 'inventory_update';
  data: {
    action: 'created' | 'updated' | 'deleted';
    item: InventoryItem;
  };
}

export interface PriceChangeMessage extends WebSocketMessage {
  type: 'price_change';
  data: {
    price_history: PriceHistory;
    inventory_item: InventoryItem;
  };
}

export interface StockAlertMessage extends WebSocketMessage {
  type: 'stock_alert';
  data: {
    alert: StockAlert;
    inventory_item: InventoryItem;
  };
}

// フィルター・ソート型
export interface InventoryFilters {
  category?: string;
  is_active?: boolean;
  is_low_stock?: boolean;
  supplier?: string;
  location?: string;
  search?: string;
}

export interface SortOptions {
  field: keyof InventoryItem;
  direction: 'asc' | 'desc';
}

// ダッシュボード統計型
export interface DashboardStats {
  total_items: number;
  low_stock_items: number;
  out_of_stock_items: number;
  total_value: number;
  recent_alerts: number;
  price_changes_today: number;
}

// エラー型
export interface APIError {
  detail: string | { [key: string]: string[] };
  code?: string;
  timestamp?: string;
}