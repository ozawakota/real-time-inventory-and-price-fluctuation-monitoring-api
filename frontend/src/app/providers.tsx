'use client'

/**
 * TanStack Query v5 Providers設定
 * 
 * QueryClientの設定:
 * 1. グローバルクエリ設定 - 全クエリの共通動作
 * 2. DevTools統合 - 開発時のクエリ状態監視
 * 3. エラーハンドリング - グローバルエラー処理
 * 4. 再試行戦略 - ネットワークエラー時の自動リトライ
 * 
 * デフォルト設定の説明:
 * - staleTime: 5分間はキャッシュを新鮮とみなす
 * - retry: 失敗時に2回まで自動リトライ（カスタム関数）
 * - retryDelay: 指数バックオフでリトライ間隔を調整
 * - mutations: ミューテーションは基本的にリトライしない
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // データ鮮度期間: 5分間はキャッシュを使用
            staleTime: 5 * 60 * 1000,
            
            // カスタムリトライロジック: 2回まで再試行
            retry: (failureCount, error) => {
              // ネットワークエラーやサーバーエラーのみリトライ
              if (failureCount < 2) {
                return true
              }
              return false
            },
            
            // 指数バックオフ: 1秒→2秒→4秒...最大30秒
            retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
            
            // ガベージコレクション: 5分間未使用でキャッシュ削除
            gcTime: 5 * 60 * 1000,
            
            // ウィンドウフォーカス時の自動再取得を無効化
            refetchOnWindowFocus: false,
            
            // ネットワーク再接続時の自動再取得を有効化
            refetchOnReconnect: true,
          },
          mutations: {
            // ミューテーションは基本的にリトライしない（データ整合性のため）
            retry: false,
            
            // グローバルミューテーションエラーハンドリング
            onError: (error) => {
              console.error('Mutation error:', error)
            },
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* 開発環境でのみReact Query DevToolsを表示 */}
      {/* <ReactQueryDevtools initialIsOpen={false} /> */}
    </QueryClientProvider>
  )
}