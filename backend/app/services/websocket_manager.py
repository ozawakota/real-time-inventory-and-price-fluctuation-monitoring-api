"""
WebSocket接続管理サービス

このファイルでは、リアルタイム通信を提供するWebSocket接続の管理を実装しています。
接続の管理、メッセージのブロードキャスト、Redis Pub/Subとの連携、
タイプ別の通知配信を担当します。

主要機能:
- WebSocket接続の管理（接続・切断・維持）
- タイプ別接続分類（在庫・価格・アラート）
- リアルタイムメッセージブロードキャスト
- Redis Pub/Sub統合（外部サービス連携）
- 接続状態の監視・統計情報
- エラーハンドリング・自動復旧

設計原則:
- ファンアウトパターン（1対多通信）
- 接続タイプ別管理
- 非同期メッセージ処理
- Redis統合によるスケーラビリティ

アーキテクチャ:
- 接続管理: WebSocket接続のライフサイクル管理
- メッセージルーティング: タイプ別通知配信
- Redis連携: 外部システムとのメッセージ交換
- 障害回復: 接続失敗時の自動クリーンアップ

技術スタック:
- FastAPI WebSocket（リアルタイム通信）
- Redis Pub/Sub（メッセージブローカー）
- Asyncio（非同期処理）
- Structlog（構造化ログ）
"""
from fastapi import WebSocket
from typing import List, Dict, Any
import json
import structlog
import asyncio
from datetime import datetime

from app.core.redis_client import redis_manager, CHANNELS

# 構造化ログ設定
logger = structlog.get_logger(__name__)


class ConnectionManager:
    """
    WebSocket接続管理マネージャークラス
    
    リアルタイム通信システムの中核となる接続管理クラスです。
    WebSocket接続のライフサイクル、メッセージ配信、Redis連携を統合管理します。
    
    接続分類:
    - inventory: 在庫情報の更新通知
    - price: 価格情報の変動通知
    - alerts: アラート・警告通知
    
    アーキテクチャパターン:
    - シングルトンパターン（接続状態の一元管理）
    - ファンアウトパターン（1対多メッセージ配信）
    - オブザーバーパターン（イベント駆動通知）
    
    スケーラビリティ:
    - 水平スケーリング対応（Redis Pub/Sub）
    - 接続プール管理
    - 自動接続復旧機能
    
    主要責務:
    1. WebSocket接続の受け入れ・管理
    2. タイプ別メッセージルーティング
    3. Redis Pub/Sub統合
    4. 接続状態監視・統計
    5. 障害処理・自動復旧
    """
    
    def __init__(self):
        """
        接続マネージャー初期化
        
        接続プールの初期化、Redis購読タスクの準備を行います。
        """
        # Store active connections by type
        self.active_connections: Dict[str, List[WebSocket]] = {
            "inventory": [],
            "price": [],
            "alerts": []
        }
        self.subscriber_task: asyncio.Task = None
        self.is_listening = False
    
    async def connect(self, websocket: WebSocket, connection_type: str = "general"):
        """
        WebSocket接続受け入れ・登録
        
        新しいWebSocket接続を受け入れ、URL基づくタイプ分類を行い、
        適切な接続プールに登録します。Redis購読も自動開始します。
        
        接続フロー:
        1. WebSocket接続の受け入れ
        2. URLパスによるタイプ自動判定
        3. タイプ別接続プールへの追加
        4. Redis購読タスクの開始（初回のみ）
        5. 接続統計の更新・ログ記録
        
        タイプ判定ロジック:
        - /inventory → "inventory" タイプ
        - /price → "price" タイプ  
        - /alert → "alerts" タイプ
        - その他 → connection_type パラメータ使用
        
        Args:
            websocket (WebSocket): WebSocket接続オブジェクト
            connection_type (str): 接続タイプ（URL判定の代替）
            
        Side Effects:
        - WebSocket接続の受け入れ
        - 接続プールへの追加
        - Redis購読タスク開始（初回）
        - 構造化ログ出力
        
        Performance:
        - 接続数に比例した軽量処理
        - Redis購読の1回のみ初期化
        """
        await websocket.accept()
        
        # Determine connection type from WebSocket path
        if "inventory" in str(websocket.url):
            connection_type = "inventory"
        elif "price" in str(websocket.url):
            connection_type = "price"
        elif "alert" in str(websocket.url):
            connection_type = "alerts"
        
        # Add to appropriate connection list
        if connection_type not in self.active_connections:
            self.active_connections[connection_type] = []
        
        self.active_connections[connection_type].append(websocket)
        
        # Start Redis subscriber if not already running
        if not self.is_listening:
            self.subscriber_task = asyncio.create_task(self._start_redis_subscriber())
            self.is_listening = True
        
        logger.info("WebSocket client connected", 
                   connection_type=connection_type,
                   total_connections=sum(len(conns) for conns in self.active_connections.values()))
    
    def disconnect(self, websocket: WebSocket):
        """
        WebSocket接続切断・削除
        
        指定されたWebSocket接続を接続プールから削除し、
        リソースクリーンアップを行います。
        
        切断処理:
        1. 全接続タイプから対象接続を検索
        2. 見つかった接続をプールから削除
        3. 接続統計の更新
        4. ログ記録
        
        Args:
            websocket (WebSocket): 切断対象のWebSocket接続
            
        Side Effects:
        - 接続プールからの削除
        - 接続統計の更新
        - 構造化ログ出力
        
        Note:
        - 接続が見つからない場合は何もしない
        - 複数タイプに同じ接続がある場合は最初の一致のみ削除
        - WebSocketリソース自体のクローズは呼び出し元で実行
        """
        for connection_type, connections in self.active_connections.items():
            if websocket in connections:
                connections.remove(websocket)
                logger.info("WebSocket client disconnected",
                           connection_type=connection_type,
                           remaining_connections=len(connections))
                break
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error("Failed to send personal message", error=str(e))
            self.disconnect(websocket)
    
    async def broadcast_to_type(self, message: Dict[str, Any], connection_type: str):
        """
        タイプ別メッセージブロードキャスト
        
        指定されたタイプの全接続に対してメッセージを一斉配信します。
        失敗した接続は自動的にクリーンアップされます。
        
        配信フロー:
        1. 指定タイプの接続一覧を取得（コピーで安全性確保）
        2. メッセージをJSON文字列に変換
        3. 全接続に対して並行送信
        4. 失敗した接続を記録
        5. 失敗した接続のクリーンアップ
        6. 配信結果のログ記録
        
        Args:
            message (Dict[str, Any]): 配信するメッセージ（辞書形式）
            connection_type (str): 対象接続タイプ（inventory/price/alerts）
            
        Side Effects:
        - 指定タイプの全クライアントにメッセージ送信
        - 失敗した接続の自動削除
        - 配信統計のログ出力
        
        Performance:
        - 接続コピーによる同期問題回避
        - 並行送信による高速配信
        - 失敗接続の自動クリーンアップ
        
        Error Handling:
        - 個別送信失敗は処理続行
        - 失敗接続は即座に削除
        - 詳細エラーログ記録
        """
        if connection_type not in self.active_connections:
            return
        
        connections = self.active_connections[connection_type].copy()
        message_str = json.dumps(message, default=str)
        
        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning("Failed to send message to WebSocket client", error=str(e))
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
        
        logger.info("Broadcasted message to WebSocket clients",
                   connection_type=connection_type,
                   successful_sends=len(connections) - len(disconnected),
                   failed_sends=len(disconnected))
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all active connections"""
        for connection_type in self.active_connections:
            await self.broadcast_to_type(message, connection_type)
    
    async def _start_redis_subscriber(self):
        """Start Redis subscriber to listen for updates"""
        try:
            # Subscribe to all relevant channels
            channels_to_subscribe = [
                CHANNELS["inventory_updates"],
                CHANNELS["price_updates"],
                CHANNELS["stock_alerts"],
                CHANNELS["price_alerts"],
                CHANNELS["system_notifications"]
            ]
            
            # Create subscriber for each channel
            subscribers = []
            for channel in channels_to_subscribe:
                pubsub = await redis_manager.subscribe_to_channel(channel)
                subscribers.append((channel, pubsub))
            
            logger.info("Started Redis subscribers for WebSocket broadcasting",
                       channels=channels_to_subscribe)
            
            # Listen for messages
            while self.is_listening:
                for channel, pubsub in subscribers:
                    try:
                        message = await asyncio.wait_for(
                            pubsub.get_message(ignore_subscribe_messages=True),
                            timeout=1.0
                        )
                        
                        if message and message.get("data"):
                            await self._handle_redis_message(channel, message["data"])
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error("Error processing Redis message", 
                                   channel=channel, error=str(e))
            
        except Exception as e:
            logger.error("Redis subscriber error", error=str(e))
        finally:
            # Cleanup subscribers
            for _, pubsub in subscribers:
                await pubsub.close()
    
    async def _handle_redis_message(self, channel: str, message_data: str):
        """Handle incoming Redis messages and broadcast to WebSocket clients"""
        try:
            message = json.loads(message_data)
            message["timestamp"] = datetime.utcnow().isoformat()
            message["channel"] = channel
            
            # Route message to appropriate WebSocket connections
            if channel == CHANNELS["inventory_updates"]:
                await self.broadcast_to_type(message, "inventory")
            elif channel == CHANNELS["price_updates"]:
                await self.broadcast_to_type(message, "price")
            elif channel in [CHANNELS["stock_alerts"], CHANNELS["price_alerts"]]:
                await self.broadcast_to_type(message, "alerts")
            elif channel == CHANNELS["system_notifications"]:
                await self.broadcast_to_all(message)
            
        except json.JSONDecodeError:
            logger.warning("Received invalid JSON message from Redis", 
                          channel=channel, message=message_data)
        except Exception as e:
            logger.error("Error handling Redis message", 
                        channel=channel, error=str(e))
    
    async def send_inventory_update(self, inventory_data: Dict[str, Any]):
        """
        在庫更新通知送信
        
        在庫情報の変更を接続中のクライアントとRedis経由で
        外部サービスに通知します。
        
        通知フロー:
        1. 標準化されたメッセージ形式を作成
        2. Redis Pub/Subで外部サービスに配信
        3. 直接接続クライアントにブロードキャスト
        
        Args:
            inventory_data (Dict[str, Any]): 在庫変更データ
            
        メッセージ形式:
        - type: "inventory_update"
        - data: 在庫変更データ
        - timestamp: ISO8601形式の送信時刻
        
        Side Effects:
        - Redis チャンネルへの配信
        - inventory タイプクライアントへの配信
        - ログ記録
        
        Use Cases:
        - 在庫数量変更時の即時通知
        - 新商品追加時の表示更新
        - 在庫状態変更時のUI更新
        """
        message = {
            "type": "inventory_update",
            "data": inventory_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Publish to Redis for other services
        await redis_manager.publish_message(CHANNELS["inventory_updates"], message)
        
        # Broadcast directly to connected clients
        await self.broadcast_to_type(message, "inventory")
    
    async def send_price_update(self, price_data: Dict[str, Any]):
        """
        価格更新通知送信
        
        価格情報の変更を接続中のクライアントとRedis経由で
        外部サービスに通知します。
        
        通知フロー:
        1. 標準化されたメッセージ形式を作成
        2. Redis Pub/Subで外部サービスに配信
        3. 直接接続クライアントにブロードキャスト
        
        Args:
            price_data (Dict[str, Any]): 価格変更データ
            
        メッセージ形式:
        - type: "price_update"
        - data: 価格変更データ
        - timestamp: ISO8601形式の送信時刻
        
        Side Effects:
        - Redis チャンネルへの配信
        - price タイプクライアントへの配信
        - ログ記録
        
        Use Cases:
        - 価格変更時の即時通知
        - 割引適用時の表示更新
        - 価格履歴更新時のチャート更新
        """
        message = {
            "type": "price_update",
            "data": price_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Publish to Redis for other services
        await redis_manager.publish_message(CHANNELS["price_updates"], message)
        
        # Broadcast directly to connected clients
        await self.broadcast_to_type(message, "price")
    
    async def send_stock_alert(self, alert_data: Dict[str, Any]):
        """
        在庫アラート通知送信
        
        在庫レベルの異常（低在庫・在庫切れ）を関係者に
        緊急通知します。重要度レベル付きで配信されます。
        
        通知フロー:
        1. アラートレベル付きメッセージ作成
        2. Redis Pub/Subで外部システムに配信
        3. alerts タイプクライアントに緊急配信
        
        Args:
            alert_data (Dict[str, Any]): 在庫アラートデータ
            
        メッセージ形式:
        - type: "stock_alert"
        - data: アラート詳細データ
        - timestamp: ISO8601形式の送信時刻
        - severity: 重要度レベル（critical/warning/info）
        
        重要度判定:
        - alert_data["alert_level"] → severityマッピング
        - デフォルト: "info"
        
        Side Effects:
        - Redis アラートチャンネルへの配信
        - alerts タイプクライアントへの緊急通知
        - アラートログ記録
        
        Use Cases:
        - 在庫切れ緊急通知
        - 低在庫警告
        - 管理者アラート
        - 自動発注トリガー
        """
        message = {
            "type": "stock_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": alert_data.get("alert_level", "info")
        }
        
        # Publish to Redis for other services
        await redis_manager.publish_message(CHANNELS["stock_alerts"], message)
        
        # Broadcast to alert connections
        await self.broadcast_to_type(message, "alerts")
    
    async def send_price_alert(self, alert_data: Dict[str, Any]):
        """
        価格変動アラート通知送信
        
        大幅な価格変動を検出した際に関係者に
        緊急通知します。変動タイプ別の重要度で配信されます。
        
        通知フロー:
        1. 変動タイプ付きメッセージ作成
        2. Redis Pub/Subで外部システムに配信
        3. alerts タイプクライアントに緊急配信
        
        Args:
            alert_data (Dict[str, Any]): 価格変動アラートデータ
            
        メッセージ形式:
        - type: "price_alert"
        - data: 変動詳細データ
        - timestamp: ISO8601形式の送信時刻
        - severity: 重要度レベル（major_change/significant_increase/significant_decrease）
        
        重要度判定:
        - alert_data["alert_type"] → severityマッピング
        - デフォルト: "info"
        
        Side Effects:
        - Redis アラートチャンネルへの配信
        - alerts タイプクライアントへの緊急通知
        - 価格変動ログ記録
        
        Use Cases:
        - 異常価格変動の緊急通知
        - 競合価格追跡アラート
        - 価格管理者への警告
        - 自動価格調整トリガー
        """
        message = {
            "type": "price_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": alert_data.get("alert_type", "info")
        }
        
        # Publish to Redis for other services
        await redis_manager.publish_message(CHANNELS["price_alerts"], message)
        
        # Broadcast to alert connections
        await self.broadcast_to_type(message, "alerts")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        接続統計情報取得
        
        現在のWebSocket接続状態とRedis購読状況の
        統計情報を取得します。監視・デバッグ用途で使用されます。
        
        統計項目:
        - 総接続数: 全タイプの接続総数
        - タイプ別接続数: inventory/price/alerts毎の接続数
        - Redis購読状態: 購読処理の稼働状況
        - 購読タスク状態: 非同期タスクの実行状況
        
        Returns:
            Dict[str, Any]: 接続統計情報辞書
            - total_connections: 総接続数
            - connections_by_type: タイプ別接続数
            - is_redis_listening: Redis購読フラグ
            - subscriber_task_running: 購読タスク稼働状況
            
        Use Cases:
        - 管理ダッシュボード表示
        - システム監視・アラート
        - 性能分析・最適化
        - デバッグ・トラブルシューティング
        
        Performance:
        - 軽量な統計計算
        - リアルタイム状態反映
        - キャッシュ不要（即座に最新状態）
        """
        return {
            "total_connections": sum(len(conns) for conns in self.active_connections.values()),
            "connections_by_type": {
                conn_type: len(conns) for conn_type, conns in self.active_connections.items()
            },
            "is_redis_listening": self.is_listening,
            "subscriber_task_running": self.subscriber_task and not self.subscriber_task.done()
        }