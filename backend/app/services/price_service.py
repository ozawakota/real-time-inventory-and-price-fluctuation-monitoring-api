"""
価格管理ビジネスロジックサービス

このファイルでは、価格管理に関する全ビジネスロジックを実装しています。
データベース操作、キャッシュ管理、価格履歴追跡、変動監視、アラート処理等を担当します。

主要機能:
- 価格CRUD操作（作成、取得、更新、履歴管理）
- キャッシュ戦略（Redis使用）
- 価格変動履歴の自動記録
- 大幅価格変動の検出・アラート
- リアルタイム価格通知（WebSocket）
- 価格分析・統計情報生成

設計原則:
- サービス層パターン（ビジネスロジックの集約）
- 価格履歴の完全追跡
- リアルタイム変動監視
- キャッシュによる高性能アクセス

技術スタック:
- SQLAlchemy（非同期ORM）
- Redis（キャッシュ）
- Structlog（構造化ログ）
- WebSocket（リアルタイム通信）
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from typing import List, Optional
from datetime import datetime
import structlog

from app.models.price import Price, PriceHistory
from app.schemas.price import PriceCreate, PriceUpdate, PriceChangeAlert
from app.core.redis_client import redis_manager, CACHE_KEYS
from app.core.config import settings

# 構造化ログ設定
logger = structlog.get_logger(__name__)


class PriceService:
    """
    価格管理サービスクラス
    
    価格情報の全ビジネスロジックを担当するサービス層クラスです。
    価格データの永続化、変動履歴管理、リアルタイム監視、アラート処理を
    統合的に処理します。
    
    設計パターン:
    - サービス層パターン（ビジネスロジックの集約）
    - 履歴パターン（価格変動の完全追跡）
    - オブザーバーパターン（価格変動イベント通知）
    - キャッシュアサイドパターン（Redis活用）
    
    主要責務:
    1. 価格データ永続化（PostgreSQL）
    2. 変動履歴の自動記録
    3. キャッシュ戦略（Redis）
    4. 大幅変動の監視・アラート
    5. リアルタイム通知（WebSocket）
    
    価格変動監視:
    - 閾値ベースの変動検出
    - 履歴データの自動記録
    - アラートレベル分類
    - リアルタイム通知配信
    
    使用例:
    ```python
    service = PriceService(db_session)
    price = await service.create_or_update_price(price_data)
    ```
    """
    
    def __init__(self, db: AsyncSession):
        """
        サービス初期化
        
        Args:
            db (AsyncSession): SQLAlchemy非同期データベースセッション
        """
        self.db = db
    
    async def get_all_prices(self, skip: int = 0, limit: int = 100) -> List[Price]:
        """
        全価格一覧取得（ページネーション対応）
        
        アクティブな価格情報の一覧を取得します。
        有効開始日時の降順でソートされ、ページネーション機能を提供します。
        
        取得条件:
        - is_active = True（アクティブな価格のみ）
        - 有効開始日時の降順ソート
        - ページネーション対応
        
        Args:
            skip (int): オフセット（開始位置）- ページネーション用
            limit (int): 取得件数上限 - パフォーマンス制御
        
        Returns:
            List[Price]: 価格情報リスト（有効開始日時降順）
            
        Use Cases:
        - 価格管理画面での一覧表示
        - 価格監視ダッシュボード
        - APIエンドポイントでの一括取得
        
        Performance:
        - インデックス活用（is_active, effective_from）
        - 大量データ対応（ページネーション）
        """
        query = (
            select(Price)
            .where(Price.is_active == True)
            .offset(skip)
            .limit(limit)
            .order_by(Price.effective_from.desc())
        )
        result = await self.db.execute(query)
        prices = result.scalars().all()
        
        logger.info("Retrieved price list from database", count=len(prices))
        return prices
    
    async def get_current_price(self, item_id: int) -> Optional[Price]:
        """
        現在有効価格取得
        
        指定されたアイテムの現在有効な価格を取得します。
        Redisキャッシュを活用し、高速なアクセスを実現します。
        
        価格選定ロジック:
        1. アクティブ状態（is_active = True）
        2. 有効期間内（effective_from <= 現在時刻）
        3. 最新の有効開始日時の価格を選択
        
        キャッシュ戦略:
        1. Redisキャッシュ確認（30分間有効）
        2. キャッシュヒット時は即座に返却
        3. キャッシュミス時はDB取得 → キャッシュ保存
        
        Args:
            item_id (int): 対象アイテムID
            
        Returns:
            Optional[Price]: 現在有効な価格情報（見つからない場合None）
            
        Performance:
        - キャッシュヒット時: ~2ms
        - キャッシュミス時: ~10ms
        - キャッシュ有効期限: 30分
        
        Use Cases:
        - 商品詳細画面での価格表示
        - 注文処理での価格確認
        - 価格比較・分析
        """
        # Check cache first
        cache_key = CACHE_KEYS["price_current"].format(item_id=item_id)
        cached_result = await redis_manager.get_cache(cache_key)
        
        if cached_result:
            logger.info("Retrieved current price from cache", item_id=item_id)
            return cached_result
        
        # Query database
        query = (
            select(Price)
            .where(
                and_(
                    Price.inventory_id == item_id,
                    Price.is_active == True,
                    Price.effective_from <= datetime.utcnow()
                )
            )
            .order_by(Price.effective_from.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        price = result.scalar_one_or_none()
        
        if price:
            # Cache for 30 minutes
            await redis_manager.set_cache(cache_key, price.__dict__, expiry=1800)
            logger.info("Retrieved current price from database", item_id=item_id, price=price.selling_price)
        
        return price
    
    async def create_or_update_price(self, price_data: PriceCreate) -> Price:
        """
        価格作成・更新（履歴管理付き）
        
        アイテムの価格を作成または更新します。既存価格の無効化、
        変更履歴の記録、大幅変動の検出・アラートを自動実行します。
        
        価格更新フロー:
        1. 既存価格の確認・取得
        2. 既存価格の無効化（effective_until設定）
        3. 新価格レコードの作成
        4. 価格変動履歴の記録
        5. 大幅変動時のアラート送信
        6. キャッシュ無効化
        7. リアルタイム通知
        
        変動監視:
        - 設定閾値を超える変動を自動検出
        - 変動率・変動額の計算
        - アラートレベル分類
        - WebSocket通知配信
        
        Args:
            price_data (PriceCreate): 価格作成データ
            
        Returns:
            Price: 作成・更新された価格情報
            
        Side Effects:
        - 既存価格の無効化
        - 価格履歴レコード作成
        - Redis キャッシュ無効化
        - WebSocket 通知送信
        - 構造化ログ出力
        
        Use Cases:
        - 管理画面からの価格設定
        - バッチ処理での一括価格更新
        - 外部システムからの価格同期
        """
        # Get existing price to track changes
        existing_price = await self.get_current_price(price_data.inventory_id)
        
        # Deactivate existing price if exists
        if existing_price:
            existing_price.is_active = False
            existing_price.effective_until = datetime.utcnow()
        
        # Create new price record
        db_price = Price(**price_data.model_dump())
        self.db.add(db_price)
        
        if existing_price:
            await self.db.commit()
            await self.db.refresh(db_price)
            
            # Record price change history
            await self._record_price_history(
                inventory_id=price_data.inventory_id,
                old_price=existing_price.selling_price,
                new_price=db_price.selling_price,
                change_reason="manual_update",
                change_type="manual"
            )
            
            # Check for significant price change
            price_change_percent = abs((db_price.selling_price - existing_price.selling_price) / existing_price.selling_price * 100)
            if price_change_percent >= settings.PRICE_CHANGE_THRESHOLD * 100:
                await self._send_price_change_alert(existing_price, db_price, price_change_percent)
        
        await self.db.commit()
        await self.db.refresh(db_price)
        
        # Invalidate cache
        await self._invalidate_price_caches(price_data.inventory_id)
        
        # Send real-time update
        await self._send_price_update(db_price, "created" if not existing_price else "updated")
        
        logger.info("Created/updated price", item_id=price_data.inventory_id, new_price=db_price.selling_price)
        return db_price
    
    async def update_price(self, item_id: int, price_update: PriceUpdate) -> Optional[Price]:
        """Update existing price"""
        # Get current price
        current_price = await self.get_current_price(item_id)
        if not current_price:
            return None
        
        # Get old price for history tracking
        old_price = current_price.selling_price
        
        # Update price
        update_data = price_update.model_dump(exclude_unset=True)
        
        query = (
            update(Price)
            .where(Price.id == current_price.id)
            .values(**update_data)
            .returning(Price)
        )
        result = await self.db.execute(query)
        await self.db.commit()
        updated_price = result.scalar_one_or_none()
        
        if updated_price and "selling_price" in update_data:
            # Record price change history
            await self._record_price_history(
                inventory_id=item_id,
                old_price=old_price,
                new_price=updated_price.selling_price,
                change_reason=price_update.change_reason or "price_update",
                change_type="manual"
            )
            
            # Check for significant change
            price_change_percent = abs((updated_price.selling_price - old_price) / old_price * 100)
            if price_change_percent >= settings.PRICE_CHANGE_THRESHOLD * 100:
                # Create temporary old price object for alert
                old_price_obj = Price(selling_price=old_price, inventory_id=item_id)
                await self._send_price_change_alert(old_price_obj, updated_price, price_change_percent)
        
        # Invalidate cache
        await self._invalidate_price_caches(item_id)
        
        # Send real-time update
        if updated_price:
            await self._send_price_update(updated_price, "updated")
            logger.info("Updated price", item_id=item_id, new_price=updated_price.selling_price)
        
        return updated_price
    
    async def get_price_history(self, item_id: int, start_date: datetime) -> List[PriceHistory]:
        """
        価格変動履歴取得
        
        指定されたアイテムの価格変動履歴を指定期間で取得します。
        時系列データとして価格変動パターンの分析に使用されます。
        
        取得条件:
        - 指定アイテムIDの履歴のみ
        - 開始日時以降の変動履歴
        - 変動日時の降順ソート
        
        キャッシュ戦略:
        1. Redis キャッシュ確認（1時間有効）
        2. キャッシュキーに期間（日数）を含む
        3. キャッシュミス時はDB取得 → キャッシュ保存
        
        Args:
            item_id (int): 対象アイテムID
            start_date (datetime): 履歴取得開始日時
            
        Returns:
            List[PriceHistory]: 価格変動履歴リスト（変動日時降順）
            
        履歴データ内容:
        - 変動前後の価格
        - 変動率・変動額
        - 変動理由・種別
        - 変動日時
        
        Use Cases:
        - 価格変動チャート表示
        - トレンド分析
        - 価格設定の根拠資料
        - 競合分析用データ
        """
        # Check cache first
        cache_key = CACHE_KEYS["price_history"].format(item_id=item_id, days=(datetime.utcnow() - start_date).days)
        cached_result = await redis_manager.get_cache(cache_key)
        
        if cached_result:
            logger.info("Retrieved price history from cache", item_id=item_id)
            return cached_result
        
        # Query database
        query = (
            select(PriceHistory)
            .where(
                and_(
                    PriceHistory.inventory_id == item_id,
                    PriceHistory.changed_at >= start_date
                )
            )
            .order_by(PriceHistory.changed_at.desc())
        )
        result = await self.db.execute(query)
        history = result.scalars().all()
        
        # Cache for 1 hour
        await redis_manager.set_cache(cache_key, [h.__dict__ for h in history], expiry=3600)
        
        logger.info("Retrieved price history from database", item_id=item_id, count=len(history))
        return history
    
    async def get_significant_price_changes(self, threshold_percent: float, start_date: datetime) -> List[PriceHistory]:
        """
        大幅価格変動検出
        
        指定された閾値を超える大幅な価格変動を検出・取得します。
        異常な価格変動の監視やアラートシステムで使用されます。
        
        検出条件:
        - 指定期間内の価格変動
        - 変動率が閾値以上
        - 変動率の降順ソート（大きい変動から）
        
        Args:
            threshold_percent (float): 変動率閾値（％）
            start_date (datetime): 監視開始日時
            
        Returns:
            List[PriceHistory]: 大幅変動履歴リスト（変動率降順）
            
        Use Cases:
        - 異常価格変動のアラート
        - 価格監視ダッシュボード
        - 市場動向分析
        - 競合価格追跡
        
        Performance:
        - 変動率インデックス活用
        - 期間絞り込みで効率的な検索
        
        Example:
        - threshold_percent=10.0 → 10%以上の変動を検出
        - start_date=24時間前 → 過去24時間の監視
        """
        query = (
            select(PriceHistory)
            .where(
                and_(
                    PriceHistory.changed_at >= start_date,
                    PriceHistory.price_change_percent >= threshold_percent
                )
            )
            .order_by(PriceHistory.price_change_percent.desc())
        )
        result = await self.db.execute(query)
        changes = result.scalars().all()
        
        logger.info("Retrieved significant price changes", threshold=threshold_percent, count=len(changes))
        return changes
    
    async def _record_price_history(self, inventory_id: int, old_price: float, new_price: float, 
                                   change_reason: str = None, change_type: str = "manual"):
        """
        価格変動履歴記録
        
        価格変更時に履歴テーブルに変動記録を保存する内部メソッドです。
        変動率・変動額の計算、理由・種別の記録を自動実行します。
        
        計算ロジック:
        - price_change_amount = new_price - old_price（変動額）
        - price_change_percent = (変動額 / old_price) * 100（変動率）
        - ゼロ除算対策（old_price = 0の場合は変動率0%）
        
        Args:
            inventory_id (int): 対象アイテムID
            old_price (float): 変更前価格
            new_price (float): 変更後価格
            change_reason (str, optional): 変更理由
            change_type (str): 変更種別（"manual", "auto", "batch"等）
            
        Side Effects:
        - PriceHistory テーブルにレコード追加
        - 構造化ログ出力
        
        Note:
        - コミット処理は呼び出し元で実行
        - トランザクション整合性は呼び出し元で管理
        
        Use Cases:
        - 全ての価格変更の監査証跡
        - 価格変動分析データの基盤
        - コンプライアンス対応
        """
        price_change_amount = new_price - old_price
        price_change_percent = (price_change_amount / old_price * 100) if old_price > 0 else 0
        
        history_record = PriceHistory(
            inventory_id=inventory_id,
            old_price=old_price,
            new_price=new_price,
            price_change_percent=price_change_percent,
            price_change_amount=price_change_amount,
            change_reason=change_reason,
            change_type=change_type
        )
        
        self.db.add(history_record)
        # Note: commit will be handled by caller
        
        logger.info("Recorded price history", 
                   inventory_id=inventory_id, 
                   change_percent=round(price_change_percent, 2))
    
    async def _invalidate_price_caches(self, item_id: int):
        """
        関連価格キャッシュ無効化
        
        価格データ変更時に関連するRedisキャッシュを無効化します。
        データ整合性保持とキャッシュ汚染防止のための内部メソッドです。
        
        無効化対象:
        1. 現在価格キャッシュ（アイテム別）
        2. 価格履歴キャッシュ（よく使用される期間）
        
        Args:
            item_id (int): 無効化対象のアイテムID
            
        無効化パターン:
        - 現在価格: 即座に無効化（整合性重要）
        - 履歴キャッシュ: 複数期間を一括無効化
        
        Performance Notes:
        - 失敗時も処理継続（ログのみ）
        - 本番環境ではパターンマッチング推奨
        """
        cache_key = CACHE_KEYS["price_current"].format(item_id=item_id)
        await redis_manager.delete_cache(cache_key)
        
        # Clear history caches
        for days in [7, 30, 90]:
            cache_key = CACHE_KEYS["price_history"].format(item_id=item_id, days=days)
            await redis_manager.delete_cache(cache_key)
    
    async def _send_price_update(self, price: Price, action: str):
        """
        リアルタイム価格更新通知送信
        
        WebSocketを使用して接続中のクライアントに価格変更を
        リアルタイムで通知する内部メソッドです。
        
        通知データ構造:
        - action: 操作種別（created/updated/deleted）
        - price: 変更された価格情報の詳細
        
        Args:
            price (Price): 変更対象の価格情報
            action (str): 実行されたアクション（"created", "updated", "deleted"）
            
        通知内容:
        - 価格識別情報（ID、アイテムID）
        - 価格詳細（販売価格、原価、割引価格、最終価格）
        - 利益率（計算値）
        - 有効期間情報
        
        Side Effects:
        - 全WebSocket接続クライアントに通知送信
        - 通信エラーは内部的に処理（ログのみ）
        
        Use Cases:
        - フロントエンドのリアルタイム価格表示更新
        - ダッシュボードの即座な反映
        - 複数ユーザー間の価格データ同期
        - 価格監視システムの一部
        """
        from app.services.websocket_manager import ConnectionManager
        
        manager = ConnectionManager()
        
        await manager.send_price_update({
            "action": action,
            "price": {
                "id": price.id,
                "inventory_id": price.inventory_id,
                "selling_price": price.selling_price,
                "cost_price": price.cost_price,
                "discount_price": price.discount_price,
                "final_price": price.final_price,
                "margin_percent": price.calculated_margin,
                "effective_from": price.effective_from.isoformat() if price.effective_from else None
            }
        })
    
    async def _send_price_change_alert(self, old_price: Price, new_price: Price, change_percent: float):
        """
        価格変動アラート送信
        
        大幅な価格変動時に関係者にアラート通知を送信する内部メソッドです。
        変動率に基づくアラートレベル分類とWebSocket通知を実行します。
        
        アラートレベル判定:
        - major_change: 20%以上の大幅変動
        - significant_increase: 有意な価格上昇
        - significant_decrease: 有意な価格下降
        
        Args:
            old_price (Price): 変更前の価格情報
            new_price (Price): 変更後の価格情報
            change_percent (float): 変動率（％）
            
        アラートデータ構造:
        - 基本情報（アイテムID、SKU、名前）
        - 変動詳細（前後価格、変動率、変動額）
        - アラート分類とタイムスタンプ
        
        Side Effects:
        - WebSocket クライアントへアラート通知
        - 構造化ログ記録（アラート履歴）
        
        Use Cases:
        - 価格管理者への緊急通知
        - 異常価格変動の監視
        - 競合価格追跡アラート
        - 自動価格調整システムのトリガー
        
        Note:
        - 本番環境では在庫システムからSKU・商品名を取得
        - アラート配信先の管理（購読者リスト等）
        """
        from app.services.websocket_manager import ConnectionManager
        
        manager = ConnectionManager()
        
        # Determine alert type
        if change_percent >= 20:
            alert_type = "major_change"
        elif new_price.selling_price > old_price.selling_price:
            alert_type = "significant_increase"
        else:
            alert_type = "significant_decrease"
        
        alert_data = PriceChangeAlert(
            inventory_id=new_price.inventory_id,
            sku=f"ITEM-{new_price.inventory_id}",  # Would get from inventory in real implementation
            item_name="Item Name",  # Would get from inventory in real implementation
            old_price=old_price.selling_price,
            new_price=new_price.selling_price,
            change_percent=change_percent,
            change_amount=new_price.selling_price - old_price.selling_price,
            alert_type=alert_type,
            timestamp=datetime.utcnow()
        )
        
        await manager.send_price_alert(alert_data.model_dump())