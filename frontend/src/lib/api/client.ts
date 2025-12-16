import axios from 'axios';
import type {
  InventoryItem,
  InventoryCreate,
  InventoryUpdate,
  PriceHistory,
  PriceHistoryCreate,
  StockAlert,
  PaginatedResponse,
  DashboardStats,
  InventoryStats,
  APIError,
} from './types';

// API クライアント設定
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});


// リクエストインターセプター
apiClient.interceptors.request.use(
  (config) => {
    // 認証トークンがある場合は追加
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// レスポンスインターセプター
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    
    // より詳細なエラー情報を作成
    const errorMessage = {
      message: 'APIエラーが発生しました',
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      url: error.config?.url,
    };
    
    if (error.response?.status === 401) {
      // 認証エラーの場合、トークンを削除してログイン画面にリダイレクト
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    } else if (error.response?.status === 500) {
      errorMessage.message = 'サーバー内部エラーが発生しました。しばらく時間をおいてから再試行してください。';
    } else if (error.response?.status === 404) {
      errorMessage.message = 'リソースが見つかりませんでした。';
    } else if (error.code === 'NETWORK_ERROR' || !error.response) {
      errorMessage.message = 'ネットワークエラーが発生しました。接続を確認してください。';
    }
    
    // エラーオブジェクトにカスタムメッセージを追加
    error.message = errorMessage.message;
    error.details = errorMessage;
    
    return Promise.reject(error);
  }
);


// 在庫管理 API
export const inventoryApi = {
  // 在庫一覧取得
  getAll: async (skip = 0, limit = 100) => {
    const response = await apiClient.get<InventoryItem[]>(
      `/inventory/?skip=${skip}&limit=${limit}`
    );
    
    // 総アイテム数を別途取得（ページネーション計算用）
    const totalResponse = await apiClient.get<InventoryItem[]>('/inventory/');
    const total = totalResponse.data.length;
    
    return {
      items: response.data,
      total,
      page: Math.floor(skip / limit) + 1,
      per_page: limit,
      pages: Math.ceil(total / limit),
    };
  },

  // 在庫詳細取得
  getById: async (id: number) => {
    const response = await apiClient.get<InventoryItem>(`/inventory/${id}`);
    return response.data;
  },

  // 在庫作成
  create: async (data: InventoryCreate) => {
    const response = await apiClient.post<InventoryItem>('/inventory/', data);
    return response.data;
  },

  // 在庫更新
  update: async (id: number, data: InventoryUpdate) => {
    const response = await apiClient.put<InventoryItem>(`/inventory/${id}`, data);
    return response.data;
  },

  // 在庫削除
  delete: async (id: number) => {
    await apiClient.delete(`/inventory/${id}`);
  },

  // 在庫検索
  search: async (query: string, skip = 0, limit = 100) => {
    const response = await apiClient.get<PaginatedResponse<InventoryItem>>(
      `/inventory/search/?q=${encodeURIComponent(query)}&skip=${skip}&limit=${limit}`
    );
    return response.data;
  },

  // 低在庫アイテム取得
  getLowStock: async () => {
    try {
      const response = await apiClient.get<InventoryItem[]>('/inventory/low-stock/alert');
      return response.data;
    } catch (error) {
      // バックエンドエラーの場合、全アイテムから低在庫を抽出
      console.warn('Low stock API failed, falling back to filtering all items');
      const allItems = await apiClient.get<InventoryItem[]>('/inventory/');
      return allItems.data.filter(item => 
        item.stock_quantity <= 0 || 
        item.stock_quantity <= (item.min_stock_level || 0)
      );
    }
  },

  // 統計情報取得
  getStats: async (): Promise<InventoryStats> => {
    const response = await apiClient.get<InventoryStats>('/inventory/stats');
    return response.data;
  },

  // SKU重複チェック
  checkSkuExists: async (sku: string): Promise<boolean> => {
    try {
      const response = await apiClient.get<{ exists: boolean }>(`/inventory/check-sku/${encodeURIComponent(sku)}`);
      return response.data.exists;
    } catch (error) {
      // APIエラーの場合、全アイテムから検索してフォールバック
      console.warn('SKU check API failed, falling back to search');
      try {
        const allItems = await apiClient.get<InventoryItem[]>('/inventory/');
        return allItems.data.some(item => item.sku === sku);
      } catch (fallbackError) {
        console.error('Fallback SKU check also failed:', fallbackError);
        return false;
      }
    }
  },
};

// 価格履歴 API
export const priceApi = {
  // 価格履歴取得
  getByInventoryId: async (inventoryId: number, skip = 0, limit = 100) => {
    const response = await apiClient.get<PaginatedResponse<PriceHistory>>(
      `/price/inventory/${inventoryId}?skip=${skip}&limit=${limit}`
    );
    return response.data;
  },

  // 価格履歴作成
  create: async (data: PriceHistoryCreate) => {
    const response = await apiClient.post<PriceHistory>('/price/', data);
    return response.data;
  },

  // 価格変更統計
  getStats: async (days = 7) => {
    const response = await apiClient.get(`/price/stats/?days=${days}`);
    return response.data;
  },
};

// アラート API
export const alertApi = {
  // アラート一覧取得
  getAll: async (skip = 0, limit = 100) => {
    const response = await apiClient.get<PaginatedResponse<StockAlert>>(
      `/alerts/?skip=${skip}&limit=${limit}`
    );
    return response.data;
  },

  // 未解決アラート取得
  getUnresolved: async () => {
    const response = await apiClient.get<StockAlert[]>('/alerts/unresolved/');
    return response.data;
  },

  // アラート解決
  resolve: async (id: number) => {
    const response = await apiClient.post<StockAlert>(`/alerts/${id}/resolve`);
    return response.data;
  },
};

// ダッシュボード API
export const dashboardApi = {
  // 統計データ取得
  getStats: async () => {
    const response = await apiClient.get<DashboardStats>('/dashboard/stats/');
    return response.data;
  },
};

// ヘルスチェック
export const healthApi = {
  check: async () => {
    const response = await apiClient.get('/health/');
    return response.data;
  },
};

export { apiClient };
export default apiClient;