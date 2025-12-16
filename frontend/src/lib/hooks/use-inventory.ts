
/**
 * Inventory Management Hooks
 * 
 * TanStack Query v5実装による在庫管理フック
 * - 型安全性のあるAPIクライアントとの連携
 * - 自動キャッシュ管理とバックグラウンド更新
 * - 楽観的更新（Optimistic Updates）
 * - リアルタイム同期とWebSocket連携
 * - エラーハンドリングとリトライ機能
 */

/**
 * TanStack Query キャッシュ戦略について:
 * 
 * 1. Query Keys構造 - 階層的キー管理
 *    - all: ['inventory'] - ルートキー
 *    - lists: [...all, 'list'] - 一覧系クエリ
 *    - details: [...all, 'detail'] - 詳細系クエリ
 *    - lowStock: [...all, 'low-stock'] - 低在庫アラート
 *    - stats: [...all, 'stats'] - 統計データ
 * 
 * 2. Stale Time設定 - データの鮮度管理
 *    - 一般データ: 5分 (定期的な更新が必要)
 *    - 低在庫アラート: 2分 (より頻繁な監視)
 *    - 統計データ: 1分 (リアルタイム性重視)
 * 
 * 3. GC Time設定 - メモリ管理
 *    - 未使用キャッシュの保持時間を制御
 *    - 10分後に自動削除でメモリ効率化
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventoryApi, type InventoryItem, type InventoryCreate, type InventoryUpdate, type InventoryStats } from '../api/client';
import { toast } from 'react-hot-toast';

/**
 * Query Keys管理 - TanStack Queryのキャッシュキー戦略
 * 
 * 階層的なキー構造により効率的なキャッシュ無効化を実現:
 * - 親キーの無効化で子キーも自動無効化
 * - フィルタリング条件を含むことで正確なキャッシュ制御
 * - TypeScript const assertionで型安全性を確保
 */
export const inventoryKeys = {
  // ベースキー - 在庫関連の全クエリのルート
  all: ['inventory'] as const,
  
  // 一覧系クエリのベースキー
  lists: () => [...inventoryKeys.all, 'list'] as const,
  
  // 具体的な一覧クエリ - ページネーションパラメータを含む
  list: (filters: { skip?: number; limit?: number }) => 
    [...inventoryKeys.lists(), filters] as const,
  
  // 詳細系クエリのベースキー
  details: () => [...inventoryKeys.all, 'detail'] as const,
  
  // 個別アイテムの詳細クエリ
  detail: (id: number) => [...inventoryKeys.details(), id] as const,
  
  // 低在庫アラートクエリ - 閾値パラメータを含む
  lowStock: (threshold?: number) => 
    [...inventoryKeys.all, 'low-stock', threshold] as const,
  
  // 統計データクエリ
  stats: () => [...inventoryKeys.all, 'stats'] as const,
};

/**
 * ページネーション対応在庫一覧取得フック
 * 
 * TanStack Query実装パターン:
 * 1. queryKey: ページネーションパラメータを含む一意キー
 * 2. queryFn: 非同期データ取得関数
 * 3. staleTime: データの鮮度期間（5分間は再取得しない）
 * 4. gcTime: ガベージコレクション期間（10分間キャッシュ保持）
 * 
 * @param skip オフセット位置（デフォルト: 0）
 * @param limit 取得件数（デフォルト: 100）
 * @returns 在庫一覧クエリ結果
 */
export function useInventoryList(skip = 0, limit = 100) {
  return useQuery({
    // キャッシュキー: ページネーション状態を含む
    queryKey: inventoryKeys.list({ skip, limit }),
    
    // データ取得関数: APIクライアント経由でデータ取得
    queryFn: async () => {
      return await inventoryApi.getAll(skip, limit);
    },
    
    // データ鮮度設定: 30秒間は自動再取得しない（短縮）
    staleTime: 30 * 1000,
    
    // ガベージコレクション: 5分間未使用でキャッシュ削除
    gcTime: 5 * 60 * 1000,
    
    // 初回データ取得を確実にする設定
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    
    // リトライ設定: 最大2回まで、短い間隔で
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
  });
}

/**
 * 単一在庫アイテム詳細取得フック
 * 
 * 条件付きクエリの実装パターン:
 * - enabled: false の場合クエリを実行しない
 * - itemId が有効な場合のみデータ取得
 * 
 * @param itemId 在庫アイテムID
 * @returns 在庫詳細クエリ結果
 */
export function useInventoryItem(itemId: number) {
  return useQuery({
    // アイテムIDを含む詳細キー
    queryKey: inventoryKeys.detail(itemId),
    
    // データ取得関数
    queryFn: async () => {
      return await inventoryApi.getById(itemId);
    },
    
    // 条件付きクエリ: itemIdが有効な場合のみ実行
    enabled: !!itemId,
    
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * 低在庫アイテム取得フック（アラート機能付き）
 * 
 * リアルタイム監視パターン:
 * 1. 短い staleTime (2分) で頻繁な更新
 * 2. refetchInterval で自動定期更新
 * 3. アラート重要度に応じたキャッシュ戦略
 * 
 * @param threshold アラート閾値（使用予定、現在は固定値）
 * @returns 低在庫アイテムクエリ結果
 */
export function useLowStockItems(threshold = 10) {
  return useQuery({
    // 閾値を含むキー（将来の機能拡張対応）
    queryKey: inventoryKeys.lowStock(threshold),
    
    queryFn: async () => {
      return await inventoryApi.getLowStock();
    },
    
    // アラート用短縮鮮度期間: 30秒間
    staleTime: 30 * 1000,
    
    // 短縮キャッシュ保持期間: 2分間
    gcTime: 2 * 60 * 1000,
    
    // 初回データ取得を確実にする
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    
    // 自動定期更新: 1分間隔でバックグラウンド更新
    refetchInterval: 1 * 60 * 1000,
    
    // リトライ設定
    retry: 2,
    retryDelay: 1000,
  });
}

/**
 * 在庫アイテム作成ミューテーション
 * 
 * TanStack Query Mutation パターン:
 * 1. mutationFn: 非同期変更処理
 * 2. onSuccess: 成功時のキャッシュ更新戦略
 * 3. onError: エラーハンドリング
 * 4. キャッシュ無効化: 関連するクエリキーを無効化
 * 5. 楽観的更新: 新規作成されたアイテムを即座にキャッシュに追加
 * 
 * @returns 作成ミューテーション
 */
export function useCreateInventoryItem() {
  const queryClient = useQueryClient();

  return useMutation({
    // 変更処理関数
    mutationFn: async (data: InventoryCreate) => {
      return await inventoryApi.create(data);
    },
    
    // 成功時のキャッシュ戦略
    onSuccess: (newItem) => {
      // 関連クエリの無効化: 一覧と低在庫アラートを再取得
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
      
      // 楽観的キャッシュ更新: 新規アイテムを詳細キャッシュに追加
      queryClient.setQueryData(inventoryKeys.detail(newItem.id), newItem);
      
      // ユーザーフィードバック
      toast.success(`アイテム「${newItem.name}」を作成しました`);
    },
    
    // エラーハンドリング
    onError: (error: any) => {
      console.error('Failed to create inventory item:', error);
      toast.error('アイテムの作成に失敗しました');
    },
  });
}

/**
 * 在庫アイテム更新ミューテーション（楽観的更新実装）
 * 
 * 楽観的更新（Optimistic Updates）の完全実装:
 * 1. onMutate: 更新前に楽観的更新実行
 * 2. onError: エラー時にロールバック
 * 3. onSuccess: 成功時に関連キャッシュ無効化
 * 4. onSettled: 最終的にデータを再同期
 * 
 * メリット:
 * - 即座にUIが更新されるため体感速度が向上
 * - ネットワーク遅延の影響を最小化
 * - エラー時の適切なロールバック
 * 
 * @returns 更新ミューテーション
 */
export function useUpdateInventoryItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ itemId, data }: { itemId: number; data: InventoryUpdate }) => {
      return await inventoryApi.update(itemId, data);
    },
    
    // 楽観的更新フェーズ: API実行前にUIを更新
    onMutate: async ({ itemId, data }) => {
      // 進行中のクエリをキャンセル（競合状態を防止）
      await queryClient.cancelQueries({ queryKey: inventoryKeys.detail(itemId) });

      // 現在の値をスナップショット（ロールバック用）
      const previousItem = queryClient.getQueryData<InventoryItem>(inventoryKeys.detail(itemId));

      // 楽観的更新: 新しい値でキャッシュを即座に更新
      if (previousItem) {
        queryClient.setQueryData(inventoryKeys.detail(itemId), {
          ...previousItem,
          ...data,
        });
      }

      // ロールバック用コンテキストを返す
      return { previousItem, itemId };
    },
    
    // エラー時ロールバック処理
    onError: (error, variables, context) => {
      // 楽観的更新をロールバック
      if (context?.previousItem) {
        queryClient.setQueryData(inventoryKeys.detail(context.itemId), context.previousItem);
      }
      console.error('Failed to update inventory item:', error);
      toast.error('アイテムの更新に失敗しました');
    },
    
    // 成功時処理
    onSuccess: (updatedItem) => {
      // 関連クエリを無効化して最新データを取得
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
      
      toast.success(`アイテム「${updatedItem.name}」を更新しました`);
    },
    
    // 最終処理（成功・失敗問わず実行）
    onSettled: (data, error, variables) => {
      // 詳細データを再同期（サーバーと確実に同期）
      queryClient.invalidateQueries({ queryKey: inventoryKeys.detail(variables.itemId) });
    },
  });
}

/**
 * Delete inventory item
 */
export function useDeleteInventoryItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (itemId: number) => {
      return await inventoryApi.delete(itemId);
    },
    onMutate: async (itemId) => {
      // Get the item name for toast message
      const item = queryClient.getQueryData<InventoryItem>(inventoryKeys.detail(itemId));
      return { itemName: item?.name || 'アイテム' };
    },
    onSuccess: (_, itemId, context) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: inventoryKeys.detail(itemId) });
      
      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
      
      toast.success(`${context?.itemName}を削除しました`);
    },
    onError: (error: any) => {
      console.error('Failed to delete inventory item:', error);
      toast.error('アイテムの削除に失敗しました');
    },
  });
}

/**
 * Bulk operations helper
 */
export function useBulkInventoryOperations() {
  const queryClient = useQueryClient();

  const bulkUpdate = useMutation({
    mutationFn: async (operations: Array<{ itemId: number; data: InventoryUpdate }>) => {
      const results = await Promise.allSettled(
        operations.map(op => inventoryApi.update(op.itemId, op.data))
      );
      
      const successful = results
        .filter((result): result is PromiseFulfilledResult<any> => result.status === 'fulfilled')
        .map(result => result.value);
      
      const failed = results.filter(result => result.status === 'rejected').length;
      
      return { successful, failed, total: operations.length };
    },
    onSuccess: ({ successful, failed, total }) => {
      // Invalidate all related queries
      queryClient.invalidateQueries({ queryKey: inventoryKeys.all });
      
      if (failed > 0) {
        toast.success(`${successful.length}/${total}件のアイテムを更新しました`);
        toast.error(`${failed}件のアイテムの更新に失敗しました`);
      } else {
        toast.success(`${total}件のアイテムを一括更新しました`);
      }
    },
    onError: () => {
      toast.error('一括更新に失敗しました');
    },
  });

  return { bulkUpdate };
}

/**
 * リアルタイム在庫更新フック
 * 
 * WebSocketとTanStack Queryの統合パターン:
 * 1. WebSocketメッセージを受信してキャッシュを更新
 * 2. アクション別キャッシュ操作戦略
 * 3. リアルタイム通知機能
 * 4. エラー時の安全な処理
 * 
 * キャッシュ更新戦略:
 * - created/updated: 詳細キャッシュ更新 + 一覧無効化
 * - deleted: 詳細キャッシュ削除 + 一覧無効化
 * 
 * @returns リアルタイム更新ハンドラー
 */
export function useInventoryRealTimeUpdates() {
  const queryClient = useQueryClient();

  const handleInventoryUpdate = (data: any) => {
    try {
      // WebSocketメッセージ形式の検証
      if (data.type === 'inventory_update' && data.data) {
        const { action, item } = data.data;
        
        switch (action) {
          case 'created':
          case 'updated':
            // 詳細キャッシュを新しいデータで更新
            queryClient.setQueryData(inventoryKeys.detail(item.id), item);
            
            // 一覧系クエリを無効化してバックグラウンド再取得
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
            break;
            
          case 'deleted':
            // 削除されたアイテムのキャッシュを完全除去
            queryClient.removeQueries({ queryKey: inventoryKeys.detail(item.id) });
            
            // 一覧を更新して削除を反映
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
            break;
        }
        
        // リアルタイム低在庫アラート表示
        if (action === 'updated' && item.is_low_stock) {
          toast.error(`⚠️ 在庫不足: ${item.name} (残り${item.available_quantity}個)`, {
            duration: 10000,
            id: `low-stock-${item.id}`, // 重複通知防止
          });
        }
      }
    } catch (error) {
      // WebSocketエラーはUIを壊さないよう安全に処理
      console.error('Error handling real-time inventory update:', error);
    }
  };

  return { handleInventoryUpdate };
}

/**
 * 在庫統計データ取得フック
 * 
 * ダッシュボード用高頻度更新パターン:
 * 1. 短い staleTime (1分) でリアルタイム性を重視
 * 2. refetchInterval で自動定期更新
 * 3. 統計データの一貫性確保
 * 
 * 用途: ダッシュボードサマリー、KPI表示
 * 
 * @returns 統計データクエリ結果
 */
export function useInventoryStats() {
  return useQuery({
    queryKey: inventoryKeys.stats(),
    
    queryFn: async () => {
      return await inventoryApi.getStats();
    },
    
    // 統計データ用短縮鮮度期間: 30秒間
    staleTime: 30 * 1000,
    
    // 統計キャッシュ保持期間: 2分間
    gcTime: 2 * 60 * 1000,
    
    // 初回データ取得を確実にする
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    
    // ダッシュボード用定期更新: 1分間隔
    refetchInterval: 1 * 60 * 1000,
    
    // リトライ設定
    retry: 2,
    retryDelay: 1000,
  });
}

/**
 * SKU重複チェック用フック
 * 
 * リアルタイム重複検証の実装パターン:
 * - 入力値変更時の即座な検証
 * - デバウンス処理で無駄なAPI呼び出しを削減
 * - 検証状態の管理とUI feedback
 * 
 * @param sku チェック対象のSKU文字列
 * @returns SKU重複チェック結果
 */
export function useSkuValidation(sku: string) {
  return useQuery({
    // SKU固有のキャッシュキー
    queryKey: ['inventory', 'sku-check', sku],
    
    // SKU重複チェック実行
    queryFn: async () => {
      if (!sku || sku.length < 2) {
        return { exists: false, valid: false, message: 'SKUを2文字以上入力してください' };
      }
      
      const exists = await inventoryApi.checkSkuExists(sku);
      
      return {
        exists,
        valid: !exists,
        message: exists 
          ? `SKU "${sku}" は既に使用されています`
          : `SKU "${sku}" は使用可能です`
      };
    },
    
    // 条件付き実行: SKUが入力されている場合のみ
    enabled: !!sku && sku.length >= 2,
    
    // キャッシュ設定: 短時間だけキャッシュ（リアルタイム性重視）
    staleTime: 30 * 1000, // 30秒
    gcTime: 2 * 60 * 1000, // 2分
    
    // リトライ設定: ネットワークエラー時のみ
    retry: (failureCount, error: any) => {
      // 400番台エラー（重複確認など）はリトライしない
      if (error?.response?.status >= 400 && error?.response?.status < 500) {
        return false;
      }
      return failureCount < 2;
    },
  });
}