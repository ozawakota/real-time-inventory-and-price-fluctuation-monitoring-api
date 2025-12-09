import { AlertTriangle, RefreshCw, X } from 'lucide-react';
import { useState } from 'react';
import type { InventoryItem } from '@/lib/api/types';

interface LowStockAlertProps {
  items: InventoryItem[];
  onRefresh?: () => void;
  className?: string;
}

export function LowStockAlert({ items, onRefresh, className = '' }: LowStockAlertProps) {
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed || items.length === 0) {
    return null;
  }

  // 在庫切れと低在庫を分類
  const outOfStock = items.filter(item => item.stock_quantity <= 0);
  const lowStock = items.filter(item => item.stock_quantity > 0 && item.stock_quantity <= item.min_stock_level);

  return (
    <div className={`bg-gradient-to-r from-red-50 to-yellow-50 dark:from-red-900/10 dark:to-yellow-900/10 border border-red-200 dark:border-red-800 rounded-lg p-6 ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <AlertTriangle className="w-6 h-6 text-red-600" />
          </div>
          
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
              在庫アラート
            </h3>
            
            <div className="space-y-4">
              {/* 在庫切れアイテム */}
              {outOfStock.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-red-700 dark:text-red-300 mb-2">
                    在庫切れ ({outOfStock.length}件)
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    {outOfStock.slice(0, 6).map((item) => (
                      <div 
                        key={item.id}
                        className="bg-red-100 dark:bg-red-900/20 rounded-md p-3 border border-red-200 dark:border-red-800"
                      >
                        <div className="text-sm font-medium text-red-800 dark:text-red-200">
                          {item.name}
                        </div>
                        <div className="text-xs text-red-600 dark:text-red-400 mt-1">
                          SKU: {item.sku} | カテゴリ: {item.category}
                        </div>
                        <div className="text-xs text-red-700 dark:text-red-300 mt-1 font-medium">
                          在庫数: 0 (最小: {item.min_stock_level})
                        </div>
                      </div>
                    ))}
                  </div>
                  {outOfStock.length > 6 && (
                    <p className="text-sm text-red-600 dark:text-red-400 mt-2">
                      他 {outOfStock.length - 6} 件の在庫切れアイテムがあります
                    </p>
                  )}
                </div>
              )}

              {/* 低在庫アイテム */}
              {lowStock.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-yellow-700 dark:text-yellow-300 mb-2">
                    低在庫警告 ({lowStock.length}件)
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    {lowStock.slice(0, 6).map((item) => (
                      <div 
                        key={item.id}
                        className="bg-yellow-100 dark:bg-yellow-900/20 rounded-md p-3 border border-yellow-200 dark:border-yellow-800"
                      >
                        <div className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                          {item.name}
                        </div>
                        <div className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                          SKU: {item.sku} | カテゴリ: {item.category}
                        </div>
                        <div className="text-xs text-yellow-700 dark:text-yellow-300 mt-1 font-medium">
                          在庫数: {item.stock_quantity} (最小: {item.min_stock_level})
                        </div>
                      </div>
                    ))}
                  </div>
                  {lowStock.length > 6 && (
                    <p className="text-sm text-yellow-600 dark:text-yellow-400 mt-2">
                      他 {lowStock.length - 6} 件の低在庫アイテムがあります
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* 推奨アクション */}
            <div className="mt-4 p-3 bg-white dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700">
              <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                推奨アクション
              </h4>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                {outOfStock.length > 0 && (
                  <li>• 在庫切れ商品の緊急調達を検討してください</li>
                )}
                {lowStock.length > 0 && (
                  <li>• 低在庫商品の追加発注を計画してください</li>
                )}
                <li>• 供給者との在庫補充スケジュールを確認してください</li>
                <li>• 在庫レベルの閾値設定を見直してください</li>
              </ul>
            </div>
          </div>
        </div>

        {/* アクションボタン */}
        <div className="flex items-start space-x-2 flex-shrink-0 ml-4">
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="btn btn-sm btn-secondary inline-flex items-center gap-1"
              title="データを更新"
            >
              <RefreshCw className="w-3 h-3" />
              更新
            </button>
          )}
          
          <button
            onClick={() => setIsDismissed(true)}
            className="btn btn-sm btn-secondary p-1"
            title="アラートを閉じる"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 統計サマリー */}
      <div className="mt-4 pt-4 border-t border-red-200 dark:border-red-800">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-lg font-bold text-red-600">
              {outOfStock.length}
            </div>
            <div className="text-xs text-red-500 dark:text-red-400">
              在庫切れ
            </div>
          </div>
          
          <div>
            <div className="text-lg font-bold text-yellow-600">
              {lowStock.length}
            </div>
            <div className="text-xs text-yellow-500 dark:text-yellow-400">
              低在庫警告
            </div>
          </div>
          
          <div>
            <div className="text-lg font-bold text-gray-600">
              {items.reduce((sum, item) => sum + item.stock_quantity, 0)}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              総在庫数
            </div>
          </div>
          
          <div>
            <div className="text-lg font-bold text-gray-600">
              ¥{items.reduce((sum, item) => sum + (item.stock_quantity * item.unit_cost), 0).toLocaleString()}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              アラート在庫価値
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}