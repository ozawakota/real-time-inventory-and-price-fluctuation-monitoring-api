import { useState } from 'react';
import { ChevronDown, ChevronUp, Package, AlertTriangle, CheckCircle } from 'lucide-react';
import type { InventoryItem, PaginatedResponse } from '@/lib/api/types';
import { Pagination } from '@/components/ui/Pagination';

interface InventoryTableProps {
  data: PaginatedResponse<InventoryItem>;
  onRefresh?: () => void;
  onPageChange?: (page: number) => void;
  onItemsPerPageChange?: (itemsPerPage: number) => void;
  className?: string;
}

interface TableHeaderProps {
  label: string;
  sortKey?: keyof InventoryItem;
  currentSort?: {
    key: keyof InventoryItem;
    direction: 'asc' | 'desc';
  };
  onSort?: (key: keyof InventoryItem) => void;
  className?: string;
}

function TableHeader({ label, sortKey, currentSort, onSort, className = '' }: TableHeaderProps) {
  const isSorted = currentSort?.key === sortKey;
  
  return (
    <th className={`px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider ${className}`}>
      {sortKey && onSort ? (
        <button
          onClick={() => onSort(sortKey)}
          className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-200"
        >
          <span>{label}</span>
          {isSorted && (
            currentSort.direction === 'asc' ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )
          )}
        </button>
      ) : (
        label
      )}
    </th>
  );
}

function StatusBadge({ item }: { item: InventoryItem }) {
  if (!item.is_active) {
    return (
      <span className="status-indicator bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
        無効
      </span>
    );
  }

  if (item.stock_quantity <= 0) {
    return (
      <span className="status-indicator status-danger">
        <AlertTriangle className="w-3 h-3 mr-1" />
        在庫切れ
      </span>
    );
  }

  if (item.stock_quantity <= item.min_stock_level) {
    return (
      <span className="status-indicator status-warning">
        <AlertTriangle className="w-3 h-3 mr-1" />
        低在庫
      </span>
    );
  }

  return (
    <span className="status-indicator status-success">
      <CheckCircle className="w-3 h-3 mr-1" />
      正常
    </span>
  );
}

function StockLevelBar({ current, min, max }: { current: number; min: number; max: number }) {
  const safeMax = max || 1; // ゼロ除算を防ぐ
  const percentage = Math.min((current / safeMax) * 100, 100);
  const isLow = current <= min;
  const isEmpty = current <= 0;

  let barColor = 'bg-green-500';
  if (isEmpty) {
    barColor = 'bg-red-500';
  } else if (isLow) {
    barColor = 'bg-yellow-500';
  }

  return (
    <div className="flex items-center space-x-2">
      <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div 
          className={`h-full ${barColor} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 dark:text-gray-400 min-w-0">
        {current}/{max}
      </span>
    </div>
  );
}

export function InventoryTable({ 
  data, 
  onRefresh, 
  onPageChange, 
  onItemsPerPageChange,
  className = '' 
}: InventoryTableProps) {
  const [sortConfig, setSortConfig] = useState<{
    key: keyof InventoryItem;
    direction: 'asc' | 'desc';
  }>({ key: 'name', direction: 'asc' });

  const handleSort = (key: keyof InventoryItem) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  // ソート済みデータ
  const sortedItems = [...(data.items || [])].sort((a, b) => {
    const aValue = a[sortConfig.key];
    const bValue = b[sortConfig.key];
    
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return sortConfig.direction === 'asc' 
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    }
    
    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return sortConfig.direction === 'asc' 
        ? aValue - bValue
        : bValue - aValue;
    }
    
    return 0;
  });

  if (!data.items || data.items.length === 0) {
    return (
      <div className={`text-center py-12 ${className}`}>
        <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-500 dark:text-gray-400">
          在庫アイテムが見つかりません
        </p>
      </div>
    );
  }

  return (
    <div className={`overflow-hidden ${className}`}>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <TableHeader 
                label="商品名" 
                sortKey="name" 
                currentSort={sortConfig}
                onSort={handleSort}
              />
              <TableHeader 
                label="SKU" 
                sortKey="sku" 
                currentSort={sortConfig}
                onSort={handleSort}
              />
              <TableHeader 
                label="カテゴリ" 
                sortKey="category" 
                currentSort={sortConfig}
                onSort={handleSort}
              />
              <TableHeader 
                label="在庫状況"
              />
              <TableHeader 
                label="在庫数" 
                sortKey="stock_quantity" 
                currentSort={sortConfig}
                onSort={handleSort}
              />
              <TableHeader 
                label="価格" 
                sortKey="cost_price" 
                currentSort={sortConfig}
                onSort={handleSort}
              />
              <TableHeader 
                label="詳細情報" 
                sortKey="category" 
                currentSort={sortConfig}
                onSort={handleSort}
              />
              <TableHeader 
                label="ステータス"
              />
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {sortedItems.map((item) => (
              <tr 
                key={item.id}
                className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {item.name}
                    </div>
                  </div>
                  {item.description && (
                    <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {item.description}
                    </div>
                  )}
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-mono text-gray-900 dark:text-white">
                    {item.sku}
                  </div>
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400">
                    {item.category}
                  </span>
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  <StockLevelBar 
                    current={item.stock_quantity || 0}
                    min={item.min_stock_level || 0}
                    max={item.max_stock_level || 1}
                  />
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900 dark:text-white">
                    <div className="font-medium">{(item.stock_quantity || 0).toLocaleString()}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      最小: {item.min_stock_level || 0} / 最大: {item.max_stock_level || 0}
                    </div>
                  </div>
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900 dark:text-white">
                    <div className="font-medium">¥{(item.cost_price || 0).toLocaleString()}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      原価: ¥{(item.cost_price || 0).toLocaleString()}
                    </div>
                  </div>
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {item.category || 'カテゴリなし'}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {item.dimensions || 'サイズ不明'}
                  </div>
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  <StatusBadge item={item} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ページネーション */}
      {onPageChange && onItemsPerPageChange && (
        <Pagination
          currentPage={data.page}
          totalPages={data.pages}
          totalItems={data.total}
          itemsPerPage={data.per_page}
          onPageChange={onPageChange}
          onItemsPerPageChange={onItemsPerPageChange}
        />
      )}
    </div>
  );
}