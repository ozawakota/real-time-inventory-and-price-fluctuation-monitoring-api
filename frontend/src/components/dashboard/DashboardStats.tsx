import { Package, AlertTriangle, DollarSign, TrendingUp } from 'lucide-react';
import type { InventoryItem, PaginatedResponse } from '@/lib/api/types';

interface DashboardStatsProps {
  inventoryData?: PaginatedResponse<InventoryItem>;
  lowStockItems?: InventoryItem[];
  className?: string;
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  description?: string;
  color: 'blue' | 'green' | 'yellow' | 'red';
  className?: string;
}

const colorClasses = {
  blue: 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400',
  green: 'bg-success-50 text-success-700 dark:bg-success-900/20 dark:text-success-400',
  yellow: 'bg-warning-50 text-warning-700 dark:bg-warning-900/20 dark:text-warning-400',
  red: 'bg-danger-50 text-danger-700 dark:bg-danger-900/20 dark:text-danger-400',
};

function StatCard({ title, value, icon, description, color, className = '' }: StatCardProps) {
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
            {title}
          </p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
            {value}
          </p>
          {description && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {description}
            </p>
          )}
        </div>
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

export function DashboardStats({
  inventoryData,
  lowStockItems,
  className = '',
}: DashboardStatsProps) {
  const totalItems = inventoryData?.total || 0;
  const lowStockCount = lowStockItems?.length || 0;
  const outOfStockCount = inventoryData?.items?.filter(item => item.stock_quantity <= 0).length || 0;
  
  // 総在庫価値を計算
  const totalValue = inventoryData?.items?.reduce((total, item) => {
    return total + (item.stock_quantity * item.unit_cost);
  }, 0) || 0;

  const stats = [
    {
      title: '総商品数',
      value: totalItems.toLocaleString(),
      icon: <Package className="w-6 h-6" />,
      description: '登録されている商品の総数',
      color: 'blue' as const,
    },
    {
      title: '低在庫アイテム',
      value: lowStockCount,
      icon: <AlertTriangle className="w-6 h-6" />,
      description: '最小在庫レベルを下回る商品',
      color: lowStockCount > 0 ? 'yellow' as const : 'green' as const,
    },
    {
      title: '在庫切れ',
      value: outOfStockCount,
      icon: <AlertTriangle className="w-6 h-6" />,
      description: '在庫数が0の商品',
      color: outOfStockCount > 0 ? 'red' as const : 'green' as const,
    },
    {
      title: '総在庫価値',
      value: `¥${totalValue.toLocaleString()}`,
      icon: <DollarSign className="w-6 h-6" />,
      description: '在庫の総価値 (仕入価格)',
      color: 'green' as const,
    },
  ];

  return (
    <div className={className}>
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        在庫サマリー
      </h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <StatCard
            key={index}
            title={stat.title}
            value={stat.value}
            icon={stat.icon}
            description={stat.description}
            color={stat.color}
          />
        ))}
      </div>

      {/* 追加の詳細情報 */}
      <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-md font-medium text-gray-900 dark:text-white">
            在庫状況の概要
          </h3>
          <TrendingUp className="w-5 h-5 text-gray-400" />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {totalItems > 0 ? Math.round(((totalItems - lowStockCount - outOfStockCount) / totalItems) * 100) : 0}%
            </div>
            <div className="text-gray-500 dark:text-gray-400">正常在庫</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">
              {totalItems > 0 ? Math.round((lowStockCount / totalItems) * 100) : 0}%
            </div>
            <div className="text-gray-500 dark:text-gray-400">低在庫警告</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">
              {totalItems > 0 ? Math.round((outOfStockCount / totalItems) * 100) : 0}%
            </div>
            <div className="text-gray-500 dark:text-gray-400">在庫切れ</div>
          </div>
        </div>
      </div>
    </div>
  );
}