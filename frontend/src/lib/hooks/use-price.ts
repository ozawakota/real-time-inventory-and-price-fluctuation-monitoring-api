/**
 * Price Management Hooks
 * 
 * React Query hooks for price operations with type safety from OpenAPI-generated types.
 * Includes price history tracking, change alerts, and real-time updates.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, type PriceItem, type PriceCreate, type PriceUpdate, type PriceHistory } from '../api/client';
import { toast } from 'react-hot-toast';

// Query keys for cache management
export const priceKeys = {
  all: ['price'] as const,
  lists: () => [...priceKeys.all, 'list'] as const,
  list: (filters: { skip?: number; limit?: number }) => 
    [...priceKeys.lists(), filters] as const,
  details: () => [...priceKeys.all, 'detail'] as const,
  detail: (itemId: number) => [...priceKeys.details(), itemId] as const,
  history: (itemId: number, days?: number) => 
    [...priceKeys.all, 'history', itemId, days] as const,
  changes: (threshold?: number, hours?: number) => 
    [...priceKeys.all, 'significant-changes', threshold, hours] as const,
};

/**
 * Get paginated price list
 */
export function usePriceList(skip = 0, limit = 100) {
  return useQuery({
    queryKey: priceKeys.list({ skip, limit }),
    queryFn: async () => {
      const response = await apiClient.getPrices(skip, limit);
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,   // 10 minutes
  });
}

/**
 * Get current price for specific item
 */
export function useItemPrice(itemId: number) {
  return useQuery({
    queryKey: priceKeys.detail(itemId),
    queryFn: async () => {
      const response = await apiClient.getItemPrice(itemId);
      return response.data;
    },
    enabled: !!itemId,
    staleTime: 2 * 60 * 1000, // 2 minutes (prices change frequently)
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
 * Real-time price updates hook
 */
export function usePriceRealTimeUpdates() {
  const queryClient = useQueryClient();

  const handlePriceUpdate = (data: any) => {
    try {
      if (data.type === 'price_update' && data.data) {
        const { action, price } = data.data;
        
        switch (action) {
          case 'created':
          case 'updated':
            // Update cache with new price data
            queryClient.setQueryData(priceKeys.detail(price.inventory_id), price);
            
            // Invalidate related queries
            queryClient.invalidateQueries({ queryKey: priceKeys.lists() });
            queryClient.invalidateQueries({ queryKey: priceKeys.history(price.inventory_id) });
            queryClient.invalidateQueries({ queryKey: priceKeys.changes() });
            break;
        }
      }
      
      // Handle price alerts
      if (data.type === 'price_alert' && data.data) {
        const alert = data.data;
        const changeText = alert.change_percent > 0 ? '値上がり' : '値下がり';
        const urgency = Math.abs(alert.change_percent) > 10 ? '⚠️' : '📊';
        
        toast(`${urgency} 価格${changeText}: ${alert.item_name}`, {
          description: `${Math.abs(alert.change_percent).toFixed(1)}% (¥${Math.abs(alert.change_amount).toLocaleString()})`,
          duration: 8000,
          id: `price-alert-${alert.inventory_id}`, // Prevent duplicate toasts
        });
        
        // Invalidate price-related queries for real-time updates
        queryClient.invalidateQueries({ queryKey: priceKeys.changes() });
      }
    } catch (error) {
      console.error('Error handling real-time price update:', error);
    }
  };

  return { handlePriceUpdate };
}