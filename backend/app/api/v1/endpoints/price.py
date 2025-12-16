"""
価格管理APIエンドポイント

このファイルでは価格管理システムのREST APIエンドポイントを定義しています。
FastAPIを使用したRESTful API設計に従い、価格情報のCRUD操作と
履歴管理、価格変動監視機能を提供します。

主要エンドポイント:
- GET /: 全価格一覧取得（ページネーション対応）
- GET /{item_id}: 単一アイテムの現在価格取得
- POST /: 新規価格作成・更新
- PUT /{item_id}: 価格更新
- GET /{item_id}/history: 価格履歴取得
- GET /changes/significant: 大幅価格変動検出

設計原則:
- RESTful API設計
- HTTP ステータスコード準拠
- 詳細なエラーメッセージ
- 履歴管理・変動追跡
- リアルタイム価格監視
- SwaggerUI対応

技術スタック:
- FastAPI（Webフレームワーク）
- Pydantic（データバリデーション）
- SQLAlchemy（ORM）
- 非同期処理
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime, timedelta

from app.db.session import get_db
from app.schemas.price import PriceCreate, PriceUpdate, PriceResponse, PriceHistoryResponse
from app.services.price_service import PriceService

# APIルーター初期化
router = APIRouter()


@router.get("/", response_model=List[PriceResponse])
async def get_all_prices(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    全価格一覧取得API
    
    ページネーション対応の全アイテム価格一覧を取得します。
    在庫アイテムと連携し、現在の販売価格情報を提供します。
    
    URL Pattern: GET /api/v1/price/
    
    Query Parameters:
        skip (int): オフセット（開始位置）- デフォルト: 0
        limit (int): 取得件数上限 - デフォルト: 100, 最大: 1000
        
    Response:
        List[PriceResponse]: 価格情報リスト
        - アイテムID、現在価格、有効期間含む
        - 更新日時降順でソート
        - 在庫情報との関連付けあり
        
    Status Codes:
        200: 正常取得（空リストも含む）
        500: サーバーエラー
        
    Example:
        GET /api/v1/price/?skip=0&limit=50
        → 最新50件の価格情報を取得
    """
    service = PriceService(db)
    return await service.get_all_prices(skip=skip, limit=limit)


@router.get("/{item_id}", response_model=PriceResponse)
async def get_item_price(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    アイテム別現在価格取得API
    
    指定されたアイテムIDの現在の販売価格を取得します。
    価格履歴から最新の有効な価格情報を返します。
    
    URL Pattern: GET /api/v1/price/{item_id}
    
    Path Parameters:
        item_id (int): 在庫アイテムID
        
    Response:
        PriceResponse: 価格情報詳細
        - 現在価格、有効期間、更新日時
        - 割引情報、変動率等の計算値
        - 関連在庫アイテム情報
        
    Status Codes:
        200: 価格取得成功
        404: 指定アイテムの価格が見つからない
        500: サーバーエラー
        
    Example:
        GET /api/v1/price/1
        → ID=1のアイテムの現在価格を取得
    """
    service = PriceService(db)
    price = await service.get_current_price(item_id)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found for this item")
    return price


@router.post("/", response_model=PriceResponse)
async def create_price(
    price: PriceCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    価格作成・更新API
    
    新規価格設定または既存価格の更新を行います。
    価格履歴管理により、全ての価格変更が記録されます。
    
    URL Pattern: POST /api/v1/price/
    
    Request Body:
        PriceCreate: 価格作成データ
        - item_id: 対象アイテムID（必須）
        - sale_price: 販売価格（必須）
        - effective_from: 有効開始日時（オプション）
        - effective_until: 有効終了日時（オプション）
        
    Response:
        PriceResponse: 作成・更新された価格情報
        - 自動生成された価格ID
        - 有効期間情報
        - 価格変動率計算
        
    Status Codes:
        201: 価格作成成功
        200: 価格更新成功
        400: 入力データエラー
        404: 対象アイテムが存在しない
        409: 価格設定の競合
        500: サーバーエラー
        
    Features:
        - 自動価格履歴記録
        - 重複期間チェック
        - 変動率自動計算
        - アラート条件評価
    """
    service = PriceService(db)
    return await service.create_or_update_price(price)


@router.put("/{item_id}", response_model=PriceResponse)
async def update_price(
    item_id: int,
    price_update: PriceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    アイテム価格更新API
    
    指定されたアイテムの現在価格を更新します。
    部分更新対応で、指定されたフィールドのみ変更されます。
    
    URL Pattern: PUT /api/v1/price/{item_id}
    
    Path Parameters:
        item_id (int): 更新対象アイテムID
        
    Request Body:
        PriceUpdate: 価格更新データ（部分更新対応）
        - sale_price: 新しい販売価格（オプション）
        - effective_from: 有効開始日時（オプション）
        - effective_until: 有効終了日時（オプション）
        
    Response:
        PriceResponse: 更新後の価格情報
        - 変更された価格詳細
        - 履歴情報更新
        - 変動率再計算結果
        
    Status Codes:
        200: 価格更新成功
        404: 指定アイテムの価格が見つからない
        400: 入力データエラー
        409: 価格期間の競合
        500: サーバーエラー
        
    Features:
        - 部分更新対応
        - 履歴自動記録
        - 変動アラート生成
        - 整合性チェック
    """
    service = PriceService(db)
    updated_price = await service.update_price(item_id, price_update)
    if not updated_price:
        raise HTTPException(status_code=404, detail="Price not found for this item")
    return updated_price


@router.get("/{item_id}/history", response_model=List[PriceHistoryResponse])
async def get_price_history(
    item_id: int,
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    価格履歴取得API
    
    指定されたアイテムの価格変動履歴を取得します。
    時系列データとして価格変動パターンの分析が可能です。
    
    URL Pattern: GET /api/v1/price/{item_id}/history
    
    Path Parameters:
        item_id (int): 対象アイテムID
        
    Query Parameters:
        days (int): 取得期間（日数）- デフォルト: 30日
        
    Response:
        List[PriceHistoryResponse]: 価格履歴リスト
        - 時系列順の価格変動記録
        - 変動率、期間情報含む
        - トレンド分析用データ
        
    Status Codes:
        200: 履歴取得成功（空リストも含む）
        404: 指定アイテムが存在しない
        400: パラメータエラー（days < 1等）
        500: サーバーエラー
        
    Use Cases:
        - 価格変動分析
        - トレンド把握
        - ダッシュボード表示
        - レポート生成
        
    Example:
        GET /api/v1/price/1/history?days=7
        → 過去7日間の価格履歴を取得
    """
    service = PriceService(db)
    start_date = datetime.utcnow() - timedelta(days=days)
    return await service.get_price_history(item_id, start_date)


@router.get("/changes/significant")
async def get_significant_price_changes(
    threshold_percent: float = 5.0,
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """
    大幅価格変動検出API
    
    指定された閾値を超える大幅な価格変動があったアイテムを検出します。
    リアルタイム価格監視システムの中核機能です。
    
    URL Pattern: GET /api/v1/price/changes/significant
    
    Query Parameters:
        threshold_percent (float): 変動率閾値（％）- デフォルト: 5.0%
        hours (int): 監視期間（時間）- デフォルト: 24時間
        
    Response:
        List[dict]: 大幅変動アイテムリスト
        - アイテム情報（ID、SKU、名前）
        - 変動詳細（変動率、前価格、現価格）
        - タイムスタンプ情報
        - アラートレベル
        
    Status Codes:
        200: 検出成功（該当なしも含む）
        400: パラメータエラー（閾値範囲外等）
        500: サーバーエラー
        
    Use Cases:
        - 価格変動アラート
        - 異常検知システム
        - 競合価格監視
        - 市場動向分析
        
    Features:
        - リアルタイム監視
        - カスタマイズ可能閾値
        - 複数期間対応
        - アラートレベル分類
        
    Example:
        GET /api/v1/price/changes/significant?threshold_percent=10.0&hours=12
        → 過去12時間で10%以上変動したアイテムを検出
    """
    service = PriceService(db)
    start_date = datetime.utcnow() - timedelta(hours=hours)
    return await service.get_significant_price_changes(threshold_percent, start_date)