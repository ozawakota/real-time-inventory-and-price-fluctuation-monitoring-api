import './globals.css'
import { Providers } from './providers'
import { Toaster } from 'react-hot-toast'

export const metadata = {
  title: 'リアルタイム在庫・価格監視システム',
  description: 'ECサイト運用における在庫・価格管理の正確性と即時性を保証するリアルタイム監視システム',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body className="font-sans">
        <Providers>
          <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            {children}
          </div>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                style: {
                  background: '#22c55e',
                },
              },
              error: {
                style: {
                  background: '#ef4444',
                },
              },
            }}
          />
        </Providers>
      </body>
    </html>
  )
}