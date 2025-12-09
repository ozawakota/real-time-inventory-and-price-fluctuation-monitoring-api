import { Wifi, WifiOff, RotateCcw } from 'lucide-react';

interface ConnectionStatusProps {
  isConnected: boolean;
  onConnect?: () => void;
  onDisconnect?: () => void;
  className?: string;
}

export function ConnectionStatus({
  isConnected,
  onConnect,
  onDisconnect,
  className = '',
}: ConnectionStatusProps) {
  return (
    <div className={`flex items-center space-x-3 ${className}`}>
      <div className="flex items-center space-x-2">
        {isConnected ? (
          <>
            <Wifi className="w-5 h-5 text-green-600" />
            <span className="text-sm text-green-600 font-medium">
              リアルタイム接続中
            </span>
          </>
        ) : (
          <>
            <WifiOff className="w-5 h-5 text-red-600" />
            <span className="text-sm text-red-600 font-medium">
              接続なし
            </span>
          </>
        )}
      </div>

      <div className="flex items-center space-x-2">
        {isConnected ? (
          <button
            onClick={onDisconnect}
            className="btn btn-sm btn-secondary"
            title="接続を切断"
          >
            切断
          </button>
        ) : (
          <button
            onClick={onConnect}
            className="btn btn-sm btn-primary inline-flex items-center gap-1"
            title="再接続"
          >
            <RotateCcw className="w-3 h-3" />
            接続
          </button>
        )}
      </div>
    </div>
  );
}