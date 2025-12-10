'use client'

import { useInventoryList, useLowStockItems } from '@/lib/hooks/use-inventory'
import { useWebSocket } from '@/lib/hooks/use-websocket'
import { usePagination } from '@/lib/hooks/use-pagination'
import { InventoryTable } from '@/components/inventory/InventoryTable'
import { DashboardStats } from '@/components/dashboard/DashboardStats'
import { LowStockAlert } from '@/components/alerts/LowStockAlert'
import { ConnectionStatus } from '@/components/ui/ConnectionStatus'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ErrorMessage } from '@/components/ui/ErrorMessage'

export default function DashboardPage() {
  // WebSocket接続
  const { isConnected, connect, disconnect } = useWebSocket()

  // ページネーション
  const {
    page,
    itemsPerPage,
    skip,
    limit,
    handlePageChange,
    handleItemsPerPageChange,
  } = usePagination({ initialItemsPerPage: 25 })

  // データ取得
  const { 
    data: inventoryData, 
    isLoading: inventoryLoading, 
    error: inventoryError,
    refetch: refetchInventory 
  } = useInventoryList(skip, limit)

  const { 
    data: lowStockItems, 
    isLoading: lowStockLoading 
  } = useLowStockItems()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* ヘッダー */}
      <PageHeader 
        title="リアルタイム在庫・価格監視システム"
        subtitle="ECサイト運用における在庫・価格管理の正確性と即時性を保証"
      >
        <ConnectionStatus 
          isConnected={isConnected}
          onConnect={connect}
          onDisconnect={disconnect}
        />
      </PageHeader>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 統計ダッシュボード */}
        <div className="mb-8">
          <DashboardStats 
            inventoryData={inventoryData}
            lowStockItems={lowStockItems}
          />
        </div>

        {/* 低在庫アラート */}
        {lowStockItems && lowStockItems.length > 0 && (
          <div className="mb-8">
            <LowStockAlert 
              items={lowStockItems}
              onRefresh={refetchInventory}
            />
          </div>
        )}

        {/* 在庫テーブル */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                在庫一覧
              </h2>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => refetchInventory()}
                  className="btn btn-secondary btn-sm"
                  disabled={inventoryLoading}
                >
                  {inventoryLoading ? (
                    <LoadingSpinner size="sm" />
                  ) : (
                    '更新'
                  )}
                </button>
              </div>
            </div>
          </div>

          <div className="p-6">
            {inventoryError ? (
              <ErrorMessage 
                title="在庫データの取得に失敗しました"
                message={inventoryError.message}
                onRetry={refetchInventory}
              />
            ) : inventoryLoading ? (
              <div className="flex justify-center py-12">
                <LoadingSpinner size="lg" />
              </div>
            ) : inventoryData ? (
              <InventoryTable 
                data={inventoryData}
                onRefresh={refetchInventory}
                onPageChange={handlePageChange}
                onItemsPerPageChange={handleItemsPerPageChange}
              />
            ) : (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                データがありません
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}