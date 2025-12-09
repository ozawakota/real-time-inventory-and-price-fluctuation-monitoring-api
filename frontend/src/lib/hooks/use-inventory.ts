/**
 * Inventory Management Hooks
 * 
 * React Query hooks for inventory operations with type safety from OpenAPI-generated types.
 * Provides caching, optimistic updates, and real-time synchronization.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventoryApi } from '../api/client';
import type { InventoryItem, InventoryCreate, InventoryUpdate, PaginatedResponse } from '../api/types';
import toast from 'react-hot-toast';

// Query keys for cache management
export const inventoryKeys = {
  all: ['inventory'] as const,
  lists: () => [...inventoryKeys.all, 'list'] as const,
  list: (filters: { skip?: number; limit?: number }) => 
    [...inventoryKeys.lists(), filters] as const,
  details: () => [...inventoryKeys.all, 'detail'] as const,
  detail: (id: number) => [...inventoryKeys.details(), id] as const,
  lowStock: () => 
    [...inventoryKeys.all, 'low-stock'] as const,
};

/**
 * Get paginated inventory list
 */
export function useInventoryList(skip = 0, limit = 100) {
  return useQuery<PaginatedResponse<InventoryItem>>({
    queryKey: inventoryKeys.list({ skip, limit }),
    queryFn: () => inventoryApi.getAll(skip, limit),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,   // 10 minutes
  });
}

/**
 * Get single inventory item by ID
 */
export function useInventoryItem(itemId: number) {
  return useQuery<InventoryItem>({
    queryKey: inventoryKeys.detail(itemId),
    queryFn: () => inventoryApi.getById(itemId),
    enabled: !!itemId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * Get low stock items with alert threshold
 */
export function useLowStockItems() {
  return useQuery<InventoryItem[]>({
    queryKey: inventoryKeys.lowStock(),
    queryFn: () => inventoryApi.getLowStock(),
    staleTime: 2 * 60 * 1000, // 2 minutes (more frequent updates for alerts)
    gcTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000, // Auto-refresh every 5 minutes
  });
}

/**
 * Create new inventory item
 */
export function useCreateInventoryItem() {
  const queryClient = useQueryClient();

  return useMutation<InventoryItem, Error, InventoryCreate>({
    mutationFn: (data: InventoryCreate) => inventoryApi.create(data),
    onSuccess: (newItem) => {
      // Invalidate and refetch inventory lists
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
      
      // Add the new item to the cache
      queryClient.setQueryData(inventoryKeys.detail(newItem.id), newItem);
      
      toast.success(`アイテム「${newItem.name}」を作成しました`);
    },
    onError: (error: any) => {
      console.error('Failed to create inventory item:', error);
      toast.error('アイテムの作成に失敗しました');
    },
  });
}

/**
 * Update existing inventory item
 */
export function useUpdateInventoryItem() {
  const queryClient = useQueryClient();

  return useMutation<InventoryItem, Error, { itemId: number; data: InventoryUpdate }>({
    mutationFn: ({ itemId, data }) => inventoryApi.update(itemId, data),
    onMutate: async ({ itemId, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: inventoryKeys.detail(itemId) });

      // Snapshot the previous value
      const previousItem = queryClient.getQueryData<InventoryItem>(inventoryKeys.detail(itemId));

      // Optimistically update to the new value
      if (previousItem) {
        queryClient.setQueryData(inventoryKeys.detail(itemId), {
          ...previousItem,
          ...data,
        });
      }

      return { previousItem, itemId };
    },
    onError: (error, variables, context) => {
      // Rollback optimistic update on error
      if (context?.previousItem) {
        queryClient.setQueryData(inventoryKeys.detail(context.itemId), context.previousItem);
      }
      console.error('Failed to update inventory item:', error);
      toast.error('アイテムの更新に失敗しました');
    },
    onSuccess: (updatedItem) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
      
      toast.success(`アイテム「${updatedItem.name}」を更新しました`);
    },
    onSettled: (data, error, variables) => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: inventoryKeys.detail(variables.itemId) });
    },
  });
}

/**
 * Delete inventory item
 */
export function useDeleteInventoryItem() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, number>({
    mutationFn: (itemId: number) => inventoryApi.delete(itemId),
    onMutate: async (itemId) => {
      // Get the item name for toast message
      const item = queryClient.getQueryData<InventoryItem>(inventoryKeys.detail(itemId));
      return { itemName: item?.name || 'アイテム' };
    },
    onSuccess: (data, itemId, context) => {
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
 * Real-time inventory updates hook
 */
export function useInventoryRealTimeUpdates() {
  const queryClient = useQueryClient();

  const handleInventoryUpdate = (data: any) => {
    try {
      if (data.type === 'inventory_update' && data.data) {
        const { action, item } = data.data;
        
        switch (action) {
          case 'created':
          case 'updated':
            // Update cache with new data
            queryClient.setQueryData(inventoryKeys.detail(item.id), item);
            // Invalidate list queries to trigger refetch
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
            break;
            
          case 'deleted':
            // Remove from cache
            queryClient.removeQueries({ queryKey: inventoryKeys.detail(item.id) });
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() });
            queryClient.invalidateQueries({ queryKey: inventoryKeys.lowStock() });
            break;
        }
        
        // Show notification for real-time updates
        if (action === 'updated' && item.is_low_stock) {
          toast.error(`⚠️ 在庫不足: ${item.name} (残り${item.available_quantity}個)`, {
            duration: 10000,
            id: `low-stock-${item.id}`, // Prevent duplicate toasts
          });
        }
      }
    } catch (error) {
      console.error('Error handling real-time inventory update:', error);
    }
  };

  return { handleInventoryUpdate };
}