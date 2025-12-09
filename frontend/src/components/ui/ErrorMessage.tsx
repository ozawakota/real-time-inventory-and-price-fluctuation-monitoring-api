import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorMessage({
  title = 'エラーが発生しました',
  message,
  onRetry,
  className = '',
}: ErrorMessageProps) {
  return (
    <div className={`flex items-center justify-center p-8 ${className}`}>
      <div className="text-center">
        <div className="flex justify-center mb-4">
          <AlertCircle className="w-12 h-12 text-red-500" />
        </div>
        
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          {title}
        </h3>
        
        <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md">
          {message}
        </p>
        
        {onRetry && (
          <button
            onClick={onRetry}
            className="btn btn-primary inline-flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            再試行
          </button>
        )}
      </div>
    </div>
  );
}