/**
 * 価格管理フック - TanStack Query v5実装
 * 
 * 価格監視とリアルタイム価格変動管理:
 * 1. 価格履歴追跡とトレンド分析
 * 2. 変動アラートと通知システム
 * 3. WebSocketリアルタイム更新
 * 4. 一括価格操作と最適化
 * 5. 価格分析とパフォーマンスメトリクス
 * 
 * TanStack Queryパターン:
 * - 階層的キャッシュ管理（price → list/detail/history）
 * - 時系列データの効率的な取得と更新
 * - 楽観的更新による即座UI反映
 * - リアルタイムWebSocket連携で価格監視
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, type PriceItem, type PriceCreate, type PriceUpdate, type PriceHistory } from '../api/client';
import { toast } from 'react-hot-toast';

/**
 * 価格関連クエリキー管理
 * 
 * 価格データの効率的キャッシュ戦略:
 * - all: 価格関連全クエリのルートキー
 * - lists: 価格一覧系クエリのベース
 * - list: ページネーション対応価格一覧
 * - details: 価格詳細系クエリのベース
 * - detail: 個別アイテムの価格詳細
 * - history: 価格履歴データ（期間指定対応）
 * - changes: 有意な価格変更アラート
 * 
 * キー設計の特徴:
 * - アイテムIDベースの精密なキャッシュ制御
 * - 時間パラメータで柔軟な履歴取得
 * - 闾値設定でカスタマイズ可能なアラート
 */
export const priceKeys = {
  // ベースキー - 価格関連の全クエリのルート
  all: ['price'] as const,
  
  // 一覧系クエリのベースキー
  lists: () => [...priceKeys.all, 'list'] as const,
  
  // ページネーション対応価格一覧
  list: (filters: { skip?: number; limit?: number }) => 
    [...priceKeys.lists(), filters] as const,
  
  // 詳細系クエリのベースキー
  details: () => [...priceKeys.all, 'detail'] as const,
  
  // 個別アイテムの価格詳細
  detail: (itemId: number) => [...priceKeys.details(), itemId] as const,
  
  // 価格履歴データ - 期間指定対応
  history: (itemId: number, days?: number) => 
    [...priceKeys.all, 'history', itemId, days] as const,
  
  // 有意な価格変更アラート - 闾値と時間範囲指定
  changes: (threshold?: number, hours?: number) => 
    [...priceKeys.all, 'significant-changes', threshold, hours] as const,
};

/**
 * ページネーション対応価格一覧取得フック
 * 
 * 価格データ取得のTanStack Queryパターン:
 * 1. ページネーションパラメータをキーに含める
 * 2. 5分間の鮮度期間で価格変更に対応
 * 3. 10分間のキャッシュ保持でメモリ効率化
 * 
 * 用途: 価格一覧表示、価格比較、一括操作用データ
 * 
 * @param skip オフセット位置（デフォルト: 0）
 * @param limit 取得件数（デフォルト: 100）
 * @returns 価格一覧クエリ結果
 */
export function usePriceList(skip = 0, limit = 100) {
  return useQuery({
    // ページネーション状態を含むキャッシュキー
    queryKey: priceKeys.list({ skip, limit }),
    
    // 価格一覧API呼び出し
    queryFn: async () => {
      const response = await apiClient.getPrices(skip, limit);
      return response.data;
    },
    
    // 価格データの鮮度期間: 5分間
    staleTime: 5 * 60 * 1000,
    
    // ガベージコレクション: 10分間未使用でキャッシュ削除
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * 特定アイテムの現在価格取得フック
 * 
 * リアルタイム価格監視のTanStack Queryパターン:
 * 1. 条件付きクエリ - itemIdが有効な場合のみ実行
 * 2. 短い鮮度期間（2分）で頻繁な価格変更に対応
 * 3. 迅速なキャッシュサイクルでメモリ効率
 * 
 * 用途: 商品詳細ページ、価格表示、リアルタイム監視
 * 
 * @param itemId 対象アイテムID
 * @returns アイテム価格クエリ結果
 */
export function useItemPrice(itemId: number) {
  return useQuery({
    // アイテムIDを含む詳細キー
    queryKey: priceKeys.detail(itemId),
    
    // 単一アイテム価格取得
    queryFn: async () => {
      const response = await apiClient.getItemPrice(itemId);
      return response.data;
    },
    
    // 条件付きクエリ: itemIdが有効な場合のみ実行
    enabled: !!itemId,
    
    // 短縮鮮度期間: 価格は頻繁に変更されるため2分間
    staleTime: 2 * 60 * 1000,
    
    // 迅速ガベージコレクション: 5分間
    gcTime: 5 * 60 * 1000,
  });
}

/**
 * Get price history for item
 */
export function usePriceHistory(itemId: number, days = 30) {
  return useQuery({
    queryKey: priceKeys.history(itemId, days),
    queryFn: async () => {
      const response = await apiClient.getPriceHistory(itemId, days);
      return response.data;
    },
    enabled: !!itemId,
    staleTime: 10 * 60 * 1000, // 10 minutes (historical data changes less frequently)
    gcTime: 30 * 60 * 1000,    // 30 minutes
  });
}

/**
 * Get significant price changes across all items
 */
export function useSignificantPriceChanges(thresholdPercent = 5.0, hours = 24) {
  return useQuery({
    queryKey: priceKeys.changes(thresholdPercent, hours),
    queryFn: async () => {
      const response = await apiClient.getSignificantPriceChanges(thresholdPercent, hours);
      return response.data;
    },
    staleTime: 5 * 60 * 1000,     // 5 minutes
    gcTime: 10 * 60 * 1000,       // 10 minutes
    refetchInterval: 10 * 60 * 1000, // Auto-refresh every 10 minutes
  });
}

/**
 * Create new price
 */
export function useCreatePrice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PriceCreate) => {
      const response = await apiClient.createPrice(data);
      return response.data;
    },
    onSuccess: (newPrice) => {
      // Update specific item price cache
      queryClient.setQueryData(priceKeys.detail(newPrice.inventory_id), newPrice);
      
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: priceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: priceKeys.history(newPrice.inventory_id) });
      queryClient.invalidateQueries({ queryKey: priceKeys.changes() });
      
      toast.success(`価格を設定しました: ¥${newPrice.final_price.toLocaleString()}`);
    },
    onError: (error: any) => {
      console.error('Failed to create price:', error);
      toast.error('価格の設定に失敗しました');
    },
  });
}

/**
 * Update existing price
 */
export function useUpdatePrice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ itemId, data }: { itemId: number; data: PriceUpdate }) => {
      const response = await apiClient.updatePrice(itemId, data);
      return response.data;
    },
    onMutate: async ({ itemId, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: priceKeys.detail(itemId) });

      // Snapshot the previous value
      const previousPrice = queryClient.getQueryData<PriceItem>(priceKeys.detail(itemId));

      // Optimistically update to the new value
      if (previousPrice && data.selling_price) {
        queryClient.setQueryData(priceKeys.detail(itemId), {
          ...previousPrice,
          ...data,
          final_price: data.selling_price, // Update final_price for optimistic UI
        });
      }

      return { previousPrice, itemId };
    },
    onError: (error, variables, context) => {
      // Rollback optimistic update on error
      if (context?.previousPrice) {
        queryClient.setQueryData(priceKeys.detail(context.itemId), context.previousPrice);
      }
      console.error('Failed to update price:', error);
      toast.error('価格の更新に失敗しました');
    },
    onSuccess: (updatedPrice, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: priceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: priceKeys.history(variables.itemId) });
      queryClient.invalidateQueries({ queryKey: priceKeys.changes() });
      
      const changePercent = variables.data.selling_price && updatedPrice.selling_price 
        ? ((updatedPrice.selling_price - (context?.previousPrice?.selling_price || 0)) / (context?.previousPrice?.selling_price || 1) * 100)
        : 0;
      
      const changeText = changePercent > 0 ? '値上げ' : changePercent < 0 ? '値下げ' : '更新';
      toast.success(`価格を${changeText}しました: ¥${updatedPrice.final_price.toLocaleString()}`);
    },
    onSettled: (data, error, variables) => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: priceKeys.detail(variables.itemId) });
    },
  });
}

/**
 * Price analytics hook
 */
export function usePriceAnalytics(itemId?: number) {
  const priceHistory = usePriceHistory(itemId!, 90); // 90 days of history
  const significantChanges = useSignificantPriceChanges(5.0, 24 * 7); // 1 week of changes
  
  const analytics = {
    // Calculate price volatility
    volatility: 0,
    trend: 'stable' as 'increasing' | 'decreasing' | 'stable',
    averagePrice: 0,
    priceRange: { min: 0, max: 0 },
    totalChanges: 0,
  };

  if (priceHistory.data && priceHistory.data.length > 1) {
    const prices = priceHistory.data.map(h => h.new_price).filter(Boolean);
    
    if (prices.length > 0) {
      analytics.averagePrice = prices.reduce((sum, price) => sum + price, 0) / prices.length;
      analytics.priceRange.min = Math.min(...prices);
      analytics.priceRange.max = Math.max(...prices);
      analytics.totalChanges = priceHistory.data.length;
      
      // Calculate volatility (standard deviation)
      const variance = prices.reduce((sum, price) => sum + Math.pow(price - analytics.averagePrice, 2), 0) / prices.length;
      analytics.volatility = Math.sqrt(variance);
      
      // Determine trend (last 7 entries)
      const recentPrices = prices.slice(-7);
      if (recentPrices.length >= 2) {
        const firstRecent = recentPrices[0];
        const lastRecent = recentPrices[recentPrices.length - 1];
        const changePercent = ((lastRecent - firstRecent) / firstRecent) * 100;
        
        if (changePercent > 2) analytics.trend = 'increasing';
        else if (changePercent < -2) analytics.trend = 'decreasing';
        else analytics.trend = 'stable';
      }
    }
  }

  return {
    priceHistory,
    significantChanges,
    analytics,
    isLoading: priceHistory.isLoading || significantChanges.isLoading,
    error: priceHistory.error || significantChanges.error,
  };
}

/**
 * Bulk price operations
 */
export function useBulkPriceOperations() {
  const queryClient = useQueryClient();

  const bulkPriceUpdate = useMutation({
    mutationFn: async (operations: Array<{ itemId: number; data: PriceUpdate }>) => {
      const results = await Promise.allSettled(
        operations.map(op => apiClient.updatePrice(op.itemId, op.data))
      );
      
      const successful = results
        .filter((result): result is PromiseFulfilledResult<any> => result.status === 'fulfilled')
        .map(result => result.value.data);
      
      const failed = results.filter(result => result.status === 'rejected').length;
      
      return { successful, failed, total: operations.length };
    },
    onSuccess: ({ successful, failed, total }) => {
      // Invalidate all price-related queries
      queryClient.invalidateQueries({ queryKey: priceKeys.all });
      
      if (failed > 0) {
        toast.success(`${successful.length}/${total}件の価格を更新しました`);
        toast.error(`${failed}件の価格更新に失敗しました`);
      } else {
        toast.success(`${total}件の価格を一括更新しました`);
      }
    },
    onError: () => {
      toast.error('一括価格更新に失敗しました');
    },
  });

  return { bulkPriceUpdate };
}

/**
 * リアルタイム価格更新フック
 * 
 * WebSocketとTanStack Queryの統合パターン:
 * 1. 価格更新WebSocketメッセージの受信処理
 * 2. 即座キャッシュ更新でUIの即応性向上
 * 3. 関連クエリの戦略的無効化
 * 4. 価格アラートとユーザー通知連携
 * 
 * キャッシュ更新戦略:
 * - 即座キャッシュ更新: 価格詳細データを即座更新
 * - 関連クエリ無効化: 一覧、履歴、変更アラートを更新
 * - アラート処理: 重要度別通知と重複防止
 * 
 * 通知戦略:
 * - 変更率による緊急度分類
 * - 価格変更情報の詳細表示
 * - 重複通知防止のユニークID管理
 * 
 * @returns リアルタイム価格更新ハンドラー
 */
export function usePriceRealTimeUpdates() {
  const queryClient = useQueryClient();

  const handlePriceUpdate = (data: any) => {
    try {
      // 価格更新メッセージ処理
      if (data.type === 'price_update' && data.data) {
        const { action, price } = data.data;
        
        switch (action) {
          case 'created':
          case 'updated':
            // 価格詳細キャッシュを新しいデータで即座更新
            queryClient.setQueryData(priceKeys.detail(price.inventory_id), price);
            
            // 関連クエリを無効化してバックグラウンド更新
            queryClient.invalidateQueries({ queryKey: priceKeys.lists() });
            queryClient.invalidateQueries({ queryKey: priceKeys.history(price.inventory_id) });
            queryClient.invalidateQueries({ queryKey: priceKeys.changes() });
            break;
        }
      }
      
      // 価格アラート処理
      if (data.type === 'price_alert' && data.data) {
        const alert = data.data;
        
        // 価格変更方向の判定
        const changeText = alert.change_percent > 0 ? '値上がり' : '値下がり';
        const changeIcon = alert.change_percent > 0 ? '📈' : '📉';
        
        // 緊急度判定: 10%以上の変更は警告
        const urgency = Math.abs(alert.change_percent) > 10 ? '⚠️' : '📃';
        
        // 詳細な価格情報を含む通知
        const percentChange = Math.abs(alert.change_percent).toFixed(1);
        const amountChange = Math.abs(alert.change_amount).toLocaleString();
        
        toast(`${urgency} ${changeIcon} 価格${changeText}: ${alert.item_name}`, {
          description: `${percentChange}% (¥${amountChange})の変更`,
          duration: 8000,
          id: `price-alert-${alert.inventory_id}-${Date.now()}`, // 重複通知防止
        });
        
        // 価格変更統計クエリを無効化して最新データ取得
        queryClient.invalidateQueries({ queryKey: priceKeys.changes() });
        
        // 当該アイテムの価格履歴も更新
        queryClient.invalidateQueries({ queryKey: priceKeys.history(alert.inventory_id) });
      }
    } catch (error) {
      // WebSocketエラーはUIを壊さないよう安全に処理
      console.error('Error handling real-time price update:', error);
    }
  };

  return { handlePriceUpdate };
}