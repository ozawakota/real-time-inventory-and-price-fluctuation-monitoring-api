import { useState, useCallback } from 'react';

interface PaginationState {
  page: number;
  itemsPerPage: number;
}

interface UsePaginationOptions {
  initialPage?: number;
  initialItemsPerPage?: number;
}

export function usePagination(options: UsePaginationOptions = {}) {
  const {
    initialPage = 1,
    initialItemsPerPage = 25,
  } = options;

  const [paginationState, setPaginationState] = useState<PaginationState>({
    page: initialPage,
    itemsPerPage: initialItemsPerPage,
  });

  // ページ変更
  const handlePageChange = useCallback((page: number) => {
    setPaginationState(prev => ({
      ...prev,
      page: Math.max(1, page),
    }));
  }, []);

  // ページサイズ変更
  const handleItemsPerPageChange = useCallback((itemsPerPage: number) => {
    setPaginationState(prev => ({
      page: 1, // ページサイズ変更時は1ページ目に戻る
      itemsPerPage: Math.max(1, itemsPerPage),
    }));
  }, []);

  // ページをリセット（検索やフィルタ変更時に使用）
  const resetPage = useCallback(() => {
    setPaginationState(prev => ({
      ...prev,
      page: 1,
    }));
  }, []);

  // API用のskip計算
  const skip = (paginationState.page - 1) * paginationState.itemsPerPage;
  const limit = paginationState.itemsPerPage;

  return {
    page: paginationState.page,
    itemsPerPage: paginationState.itemsPerPage,
    skip,
    limit,
    handlePageChange,
    handleItemsPerPageChange,
    resetPage,
  };
}