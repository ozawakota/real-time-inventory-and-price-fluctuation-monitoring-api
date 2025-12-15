# TanStack Query実装詳細

リアルタイム在庫・価格変動監視システムにおけるTanStack Query v5の実装パターンと最適化戦略

## 📋 目次

1. [概要と設計思想](#概要と設計思想)
2. [キャッシュ戦略](#キャッシュ戦略)
3. [フック実装パターン](#フック実装パターン)
4. [楽観的更新](#楽観的更新)
5. [リアルタイム統合](#リアルタイム統合)
6. [エラーハンドリング](#エラーハンドリング)
7. [パフォーマンス最適化](#パフォーマンス最適化)

---

## 概要と設計思想

### 🎯 設計目標

1. **データの一貫性**: サーバーとクライアントの状態同期
2. **ユーザー体験**: 即応性とスムーズな操作感
3. **開発者体験**: 型安全性とメンテナンス性
4. **パフォーマンス**: 効率的なネットワーク利用とメモリ管理

### 🏗️ アーキテクチャ概要

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │ ←→ │ TanStack Query  │ ←→ │   Backend API   │
└─────────────────┘    │   Cache Layer   │    └─────────────────┘
         ↕              └─────────────────┘             ↕
┌─────────────────┐              ↕                ┌─────────────────┐
│  User Actions   │    ┌─────────────────┐       │   Database      │
└─────────────────┘    │   WebSocket     │       └─────────────────┘
                       │  Real-time Sync │
                       └─────────────────┘
```

---

## キャッシュ戦略

### 🗝️ Query Keys設計

#### 階層的キー構造
```typescript
export const inventoryKeys = {
  // レベル1: ドメインルート
  all: ['inventory'] as const,
  
  // レベル2: 機能別グループ
  lists: () => [...inventoryKeys.all, 'list'] as const,
  details: () => [...inventoryKeys.all, 'detail'] as const,
  stats: () => [...inventoryKeys.all, 'stats'] as const,
  
  // レベル3: 具体的なクエリ
  list: (filters: { skip?: number; limit?: number }) => 
    [...inventoryKeys.lists(), filters] as const,
  detail: (id: number) => 
    [...inventoryKeys.details(), id] as const,
  lowStock: (threshold?: number) => 
    [...inventoryKeys.all, 'low-stock', threshold] as const,
};
```

#### キー設計の利点
- **効率的無効化**: `inventoryKeys.lists()`で一覧系を一括無効化
- **細粒度制御**: 個別アイテムのみを更新可能
- **型安全性**: TypeScript `const assertion`で型推論

### 📊 データ鮮度管理

#### StaleTime戦略
```typescript
// 用途別のstaleTime設定
const staleTimeConfig = {
  // リアルタイム性重視
  stats: 1 * 60 * 1000,        // 1分
  lowStockAlert: 2 * 60 * 1000, // 2分
  
  // バランス型
  inventoryList: 5 * 60 * 1000, // 5分
  inventoryDetail: 5 * 60 * 1000,
  
  // 長期キャッシュ
  priceHistory: 10 * 60 * 1000, // 10分
  priceStats: 10 * 60 * 1000,
};
```

#### GcTime戦略
```typescript
// メモリ管理のgcTime設定
const gcTimeConfig = {
  // 短期メモリ
  priceDetail: 5 * 60 * 1000,   // 5分
  
  // 標準メモリ
  inventoryDetail: 10 * 60 * 1000, // 10分
  inventoryList: 10 * 60 * 1000,
  
  // 長期メモリ
  priceStats: 30 * 60 * 1000,   // 30分
};
```

---

## フック実装パターン

### 🔍 Query Hooks

#### 基本的な取得パターン
```typescript
export function useInventoryList(skip = 0, limit = 100) {
  return useQuery({
    queryKey: inventoryKeys.list({ skip, limit }),
    queryFn: async () => {
      return await inventoryApi.getAll(skip, limit);
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}
```

#### 条件付きクエリパターン
```typescript
export function useInventoryItem(itemId: number) {
  return useQuery({
    queryKey: inventoryKeys.detail(itemId),
    queryFn: async () => {
      return await inventoryApi.getById(itemId);
    },
    enabled: !!itemId, // itemIdが有効な場合のみ実行
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}
```

#### 自動更新パターン
```typescript
export function useLowStockItems(threshold = 10) {
  return useQuery({
    queryKey: inventoryKeys.lowStock(threshold),
    queryFn: async () => {
      return await inventoryApi.getLowStock();
    },
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000, // 5分間隔で自動更新
  });
}
```

### ✏️ Mutation Hooks

#### 基本的な作成パターン
```typescript
export function useCreateInventoryItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: InventoryCreate) => {
      return await inventoryApi.create(data);
    },
    onSuccess: (newItem) => {
      // 関連クエリの無効化
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
      
      // 新アイテムをキャッシュに追加
      queryClient.setQueryData(inventoryKeys.detail(newItem.id), newItem);
      
      toast.success(`アイテム「${newItem.name}」を作成しました`);
    },
    onError: (error: any) => {
      console.error('Failed to create inventory item:', error);
      toast.error('アイテムの作成に失敗しました');
    },
  });
}
```

---

## 楽観的更新

### 🚀 完全な楽観的更新実装

#### 更新フローの詳細
```typescript
export function useUpdateInventoryItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ itemId, data }: { itemId: number; data: InventoryUpdate }) => {
      return await inventoryApi.update(itemId, data);
    },
    
    // 1. 事前処理（楽観的更新）
    onMutate: async ({ itemId, data }) => {
      // 競合を防ぐため進行中のクエリをキャンセル
      await queryClient.cancelQueries({ queryKey: inventoryKeys.detail(itemId) });

      // ロールバック用のスナップショット
      const previousItem = queryClient.getQueryData<InventoryItem>(
        inventoryKeys.detail(itemId)
      );

      // UIを即座に更新
      if (previousItem) {
        queryClient.setQueryData(inventoryKeys.detail(itemId), {
          ...previousItem,
          ...data,
        });
      }

      return { previousItem, itemId };
    },
    
    // 2. エラー時（ロールバック）
    onError: (error, variables, context) => {
      // 楽観的更新を取り消し
      if (context?.previousItem) {
        queryClient.setQueryData(
          inventoryKeys.detail(context.itemId), 
          context.previousItem
        );
      }
      console.error('Failed to update inventory item:', error);
      toast.error('アイテムの更新に失敗しました');
    },
    
    // 3. 成功時
    onSuccess: (updatedItem) => {
      // 関連クエリを無効化
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
      
      toast.success(`アイテム「${updatedItem.name}」を更新しました`);
    },
    
    // 4. 最終処理（成功・失敗問わず）
    onSettled: (data, error, variables) => {
      // サーバーとの最終同期
      queryClient.invalidateQueries({ 
        queryKey: inventoryKeys.detail(variables.itemId) 
      });
    },
  });
}
```

### 📊 楽観的更新のメリット

1. **即応性**: ネットワーク待機なしでUIが更新
2. **ユーザー体験**: スムーズで自然な操作感
3. **エラー処理**: 失敗時の適切なロールバック
4. **データ整合性**: 最終的にサーバーと同期

---

## リアルタイム統合

### 🌐 WebSocket + TanStack Query統合

#### リアルタイム更新ハンドラー
```typescript
export function useInventoryRealTimeUpdates() {
  const queryClient = useQueryClient();

  const handleInventoryUpdate = (data: any) => {
    try {
      if (data.type === 'inventory_update' && data.data) {
        const { action, item } = data.data;
        
        switch (action) {
          case 'created':
          case 'updated':
            // 詳細キャッシュを即座に更新
            queryClient.setQueryData(inventoryKeys.detail(item.id), item);
            
            // 関連クエリをバックグラウンド更新
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
            break;
            
          case 'deleted':
            // 削除されたアイテムのキャッシュを除去
            queryClient.removeQueries({ queryKey: inventoryKeys.detail(item.id) });
            
            // 一覧クエリを更新
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
            break;
        }
        
        // リアルタイム通知
        if (action === 'updated' && item.is_low_stock) {
          toast.error(`⚠️ 在庫不足: ${item.name} (残り${item.available_quantity}個)`, {
            duration: 10000,
            id: `low-stock-${item.id}`,
          });
        }
      }
    } catch (error) {
      console.error('Error handling real-time inventory update:', error);
    }
  };

  return { handleInventoryUpdate };
}
```

#### WebSocket統合のポイント

1. **即座更新**: `setQueryData`で瞬時にキャッシュ更新
2. **バックグラウンド同期**: `invalidateQueries`で関連データ更新
3. **安全なエラー処理**: WebSocketエラーがUIを破壊しない
4. **通知統合**: 重要な変更をユーザーに即座通知

---

## エラーハンドリング

### 🛡️ 多層エラー処理

#### 1. グローバルレベル（QueryClient設定）
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // カスタムリトライロジック
      retry: (failureCount, error) => {
        if (failureCount < 2) {
          return true;
        }
        return false;
      },
      
      // 指数バックオフ
      retryDelay: (attemptIndex) => 
        Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      // ミューテーションは基本的にリトライしない
      retry: false,
      
      // グローバルエラーハンドリング
      onError: (error) => {
        console.error('Mutation error:', error);
      },
    },
  },
});
```

#### 2. APIレベル（Axiosインターセプター）
```typescript
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    
    const errorMessage = {
      message: 'APIエラーが発生しました',
      status: error.response?.status,
      data: error.response?.data,
    };
    
    if (error.response?.status === 401) {
      // 認証エラー処理
      localStorage.removeItem('token');
      window.location.href = '/login';
    } else if (error.response?.status === 500) {
      errorMessage.message = 'サーバー内部エラーが発生しました';
    }
    
    error.message = errorMessage.message;
    return Promise.reject(error);
  }
);
```

#### 3. フックレベル（個別エラー処理）
```typescript
export function useInventoryList(skip = 0, limit = 100) {
  return useQuery({
    queryKey: inventoryKeys.list({ skip, limit }),
    queryFn: async () => {
      try {
        return await inventoryApi.getAll(skip, limit);
      } catch (error) {
        // 個別エラー処理
        console.error('Failed to fetch inventory list:', error);
        throw error; // TanStack Queryのエラー処理に委譲
      }
    },
    // その他の設定...
  });
}
```

---

## パフォーマンス最適化

### ⚡ メモリ最適化

#### 1. キャッシュサイズ管理
```typescript
// 大量データ対応のキャッシュ設定
const optimizedCacheConfig = {
  // 短時間キャッシュ: リアルタイムデータ
  realtime: {
    staleTime: 30 * 1000,      // 30秒
    gcTime: 2 * 60 * 1000,     // 2分
  },
  
  // 中期キャッシュ: 標準データ
  standard: {
    staleTime: 5 * 60 * 1000,  // 5分
    gcTime: 10 * 60 * 1000,    // 10分
  },
  
  // 長期キャッシュ: 静的データ
  static: {
    staleTime: 30 * 60 * 1000, // 30分
    gcTime: 60 * 60 * 1000,    // 60分
  },
};
```

#### 2. 選択的データ取得
```typescript
// 必要なフィールドのみ取得
export function useInventoryListOptimized(skip = 0, limit = 100) {
  return useQuery({
    queryKey: inventoryKeys.list({ skip, limit, fields: 'essential' }),
    queryFn: async () => {
      // 必要最小限のフィールドのみ要求
      return await inventoryApi.getAllOptimized(skip, limit, {
        fields: ['id', 'name', 'stock_quantity', 'is_low_stock']
      });
    },
    select: (data) => {
      // クライアントサイドでの追加フィルタリング
      return data.items.filter(item => item.is_active);
    },
  });
}
```

### 🚀 ネットワーク最適化

#### 1. バッチリクエスト
```typescript
// 複数アイテムの詳細を一括取得
export function useInventoryItemsBatch(itemIds: number[]) {
  return useQuery({
    queryKey: ['inventory', 'batch', itemIds.sort()],
    queryFn: async () => {
      return await inventoryApi.getBatch(itemIds);
    },
    enabled: itemIds.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}
```

#### 2. プリフェッチング
```typescript
// 次ページのプリフェッチ
export function useInventoryListWithPrefetch(skip = 0, limit = 100) {
  const queryClient = useQueryClient();
  
  const query = useQuery({
    queryKey: inventoryKeys.list({ skip, limit }),
    queryFn: async () => {
      return await inventoryApi.getAll(skip, limit);
    },
  });
  
  // 次ページを事前取得
  React.useEffect(() => {
    if (query.data && query.data.pages > Math.ceil(skip / limit) + 1) {
      queryClient.prefetchQuery({
        queryKey: inventoryKeys.list({ skip: skip + limit, limit }),
        queryFn: () => inventoryApi.getAll(skip + limit, limit),
      });
    }
  }, [skip, limit, query.data, queryClient]);
  
  return query;
}
```

---

## 📈 監視とデバッグ

### 🔍 開発者ツール

#### React Query DevToolsの活用
```typescript
// 開発環境でのみDevToolsを有効化
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
```

#### カスタムデバッグフック
```typescript
export function useQueryDebug() {
  const queryClient = useQueryClient();
  
  return {
    getCacheInfo: () => {
      const cache = queryClient.getQueryCache();
      return {
        queriesCount: cache.getAll().length,
        queries: cache.getAll().map(query => ({
          queryKey: query.queryKey,
          state: query.state,
          dataUpdatedAt: query.state.dataUpdatedAt,
        })),
      };
    },
    
    invalidateAll: () => {
      queryClient.invalidateQueries();
    },
    
    clearCache: () => {
      queryClient.clear();
    },
  };
}
```

---

## 🎯 ベストプラクティス

### ✅ 推奨パターン

1. **型安全性の確保**
   ```typescript
   // 型推論を活用
   const { data, isLoading, error } = useInventoryList();
   // data は自動的に PaginatedResponse<InventoryItem> 型
   ```

2. **エラー境界の設定**
   ```typescript
   // 各主要コンポーネントでエラーハンドリング
   if (error) {
     return <ErrorMessage error={error} onRetry={refetch} />;
   }
   ```

3. **ローディング状態の適切な表示**
   ```typescript
   if (isLoading) {
     return <LoadingSpinner />;
   }
   ```

### ❌ アンチパターン

1. **過度なrefetch**
   ```typescript
   // ❌ 悪い例
   useEffect(() => {
     refetch(); // 毎回手動でrefetch
   }, [someState]);
   
   // ✅ 良い例
   // TanStack Queryの自動更新に任せる
   ```

2. **不適切なキー設計**
   ```typescript
   // ❌ 悪い例
   queryKey: ['inventory', Math.random()]
   
   // ✅ 良い例
   queryKey: inventoryKeys.list({ skip, limit })
   ```

3. **直接的なキャッシュ操作**
   ```typescript
   // ❌ 悪い例
   queryClient.setQueryData(['inventory'], modifiedData);
   
   // ✅ 良い例
   queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
   ```

---

この実装により、リアルタイム在庫監視システムとして高いパフォーマンス、保守性、ユーザー体験を実現しています。