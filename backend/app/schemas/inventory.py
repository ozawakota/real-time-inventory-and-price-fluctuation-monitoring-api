"""
在庫管理システム用Pydanticスキーマ定義

このファイルでは、在庫データのバリデーション、シリアライゼーション、
ドキュメント生成のためのスキーマを定義しています。

主要なスキーマ:
- InventoryBase: 共通の基本フィールド
- InventoryCreate: 新規作成用（全フィールド必須）
- InventoryUpdate: 部分更新用（全フィールドオプション）
- InventoryResponse: API応答用（計算フィールド含む）
- InventoryStockAlert: 在庫アラート用
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class InventoryBase(BaseModel):
    """
    在庫アイテムの基本スキーマクラス
    
    全ての在庫関連スキーマの基底クラスとして機能します。
    共通フィールドとバリデーションルールを定義しています。
    
    フィールド詳細:
    - sku: 商品コード（Stock Keeping Unit）- ユニーク制約
    - name: 商品名 - 表示用の正式名称
    - description: 商品説明 - 詳細情報（オプション）
    - category: カテゴリ - 分類用（electronics, furniture等）
    - weight: 重量 - 配送計算用（グラム単位）
    - dimensions: 寸法 - 保管・配送用（文字列形式）
    - cost_price: 原価 - 利益計算用
    - min_stock_level: 最小在庫レベル - アラート閾値
    - max_stock_level: 最大在庫レベル - 過剰在庫防止
    - is_active: アクティブフラグ - 販売可能状態
    - is_trackable: 追跡可能フラグ - 在庫管理対象
    """
    # 商品識別情報
    sku: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="商品コード（SKU）- ユニークな商品識別子",
        example="PROD-001"
    )
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="商品名 - 表示用の正式名称",
        example="ワイヤレスヘッドホン"
    )
    description: Optional[str] = Field(
        None,
        description="商品説明 - 詳細情報（オプション）",
        example="高音質ノイズキャンセリング機能付き"
    )
    category: Optional[str] = Field(
        None, 
        max_length=100,
        description="カテゴリ - 商品分類",
        example="electronics"
    )
    
    # 物理的特性
    weight: Optional[float] = Field(
        None, 
        gt=0,
        description="重量（グラム単位）- 配送計算用",
        example=250.0
    )
    dimensions: Optional[str] = Field(
        None, 
        max_length=100,
        description="寸法 - 保管・配送用（自由形式）",
        example="20cm x 18cm x 8cm"
    )
    
    # 価格・在庫管理
    cost_price: float = Field(
        0.0, 
        ge=0,
        description="原価 - 利益計算・価格設定用",
        example=8000.0
    )
    min_stock_level: int = Field(
        10, 
        ge=0,
        description="最小在庫レベル - 低在庫アラート閾値",
        example=10
    )
    max_stock_level: int = Field(
        1000, 
        gt=0,
        description="最大在庫レベル - 過剰在庫防止",
        example=200
    )
    
    # 状態管理フラグ
    is_active: bool = Field(
        True,
        description="アクティブフラグ - 販売可能状態",
        example=True
    )
    is_trackable: bool = Field(
        True,
        description="追跡可能フラグ - 在庫管理対象かどうか",
        example=True
    )


class InventoryCreate(InventoryBase):
    """
    在庫アイテム新規作成用スキーマ
    
    新しい在庫アイテムを作成する際に使用されるスキーマです。
    InventoryBaseの全フィールドに加えて、在庫数量関連の必須フィールドを含みます。
    
    追加フィールド:
    - stock_quantity: 実在庫数 - 物理的に存在する商品数
    - reserved_quantity: 予約済み数量 - 注文済みだが未出荷の数量
    
    計算ロジック:
    available_quantity = stock_quantity - reserved_quantity
    （利用可能数量は自動計算されます）
    
    用途:
    - POST /api/v1/inventory/ エンドポイント
    - 新商品登録時のバリデーション
    - SwaggerUI でのAPI仕様表示
    """
    # 在庫数量管理
    stock_quantity: int = Field(
        0, 
        ge=0,
        description="実在庫数 - 物理的に存在する商品数量",
        example=50
    )
    reserved_quantity: int = Field(
        0, 
        ge=0,
        description="予約済み数量 - 注文済みだが未出荷の数量",
        example=5
    )
    
    # SwaggerUI での表示用設定
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sku": "PROD-001",
                "name": "ワイヤレスヘッドホン プレミアム",
                "description": "高音質ノイズキャンセリング機能付きワイヤレスヘッドホン",
                "category": "electronics",
                "stock_quantity": 50,
                "reserved_quantity": 5,
                "weight": 250.0,
                "dimensions": "20cm x 18cm x 8cm",
                "cost_price": 8000.0,
                "min_stock_level": 10,
                "max_stock_level": 200,
                "is_active": True,
                "is_trackable": True
            }
        }
    )


class InventoryUpdate(BaseModel):
    """
    在庫アイテム部分更新用スキーマ
    
    既存の在庫アイテムを部分的に更新する際に使用されるスキーマです。
    全てのフィールドがOptional（任意）となっており、変更したいフィールドのみ指定可能です。
    
    部分更新の特徴:
    - 指定されたフィールドのみ更新
    - 未指定フィールドは既存値を保持
    - SKU重複チェックあり（変更時のみ）
    - available_quantityは自動再計算
    
    用途:
    - PUT /api/v1/inventory/{item_id} エンドポイント
    - 既存商品の情報変更
    - 在庫数調整、価格変更等
    
    使用例:
    - SKUのみ変更: {"sku": "NEW-SKU-001"}
    - 価格のみ変更: {"cost_price": 7500.0}
    - 複数フィールド: {"name": "新商品名", "stock_quantity": 100}
    """
    # 商品識別情報（部分更新対応）
    sku: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=100,
        description="商品コード（SKU）- 重複チェックあり",
        example="UPDATED-SKU-001"
    )
    name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=255,
        description="商品名の更新",
        example="更新された商品名"
    )
    description: Optional[str] = Field(
        None,
        description="商品説明の更新",
        example="新しい商品説明"
    )
    category: Optional[str] = Field(
        None, 
        max_length=100,
        description="カテゴリの変更",
        example="new_category"
    )
    
    # 在庫数量管理（部分更新対応）
    stock_quantity: Optional[int] = Field(
        None, 
        ge=0,
        description="実在庫数の調整",
        example=25
    )
    reserved_quantity: Optional[int] = Field(
        None, 
        ge=0,
        description="予約済み数量の調整",
        example=3
    )
    
    # 物理的特性（部分更新対応）
    weight: Optional[float] = Field(
        None, 
        gt=0,
        description="重量の修正",
        example=280.0
    )
    dimensions: Optional[str] = Field(
        None, 
        max_length=100,
        description="寸法の修正",
        example="22cm x 20cm x 9cm"
    )
    
    # 価格・在庫管理（部分更新対応）
    cost_price: Optional[float] = Field(
        None, 
        ge=0,
        description="原価の変更",
        example=5500.0
    )
    min_stock_level: Optional[int] = Field(
        None, 
        ge=0,
        description="最小在庫レベルの調整",
        example=5
    )
    max_stock_level: Optional[int] = Field(
        None, 
        gt=0,
        description="最大在庫レベルの調整",
        example=150
    )
    
    # 状態管理フラグ（部分更新対応）
    is_active: Optional[bool] = Field(
        None,
        description="アクティブ状態の切り替え",
        example=False
    )
    is_trackable: Optional[bool] = Field(
        None,
        description="追跡可能状態の切り替え",
        example=True
    )
    
    # SwaggerUI での部分更新例
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sku": "UPDATED-SKU-001",
                "name": "更新された商品名",
                "cost_price": 5500.0,
                "stock_quantity": 25
            }
        }
    )


class InventoryResponse(InventoryBase):
    """
    在庫アイテムAPI応答用スキーマ
    
    APIエンドポイントからの応答データ形式を定義するスキーマです。
    InventoryBaseの全フィールドに加えて、ID、計算フィールド、
    タイムスタンプ等の応答専用フィールドを含みます。
    
    応答専用フィールド:
    - id: データベース主キー
    - stock_quantity: 実在庫数
    - reserved_quantity: 予約済み数量
    - available_quantity: 利用可能数量（計算値）
    - created_at: 作成日時
    - updated_at: 最終更新日時
    - is_low_stock: 低在庫フラグ（計算値）
    - stock_status: 在庫ステータス（計算値）
    
    計算ロジック:
    - available_quantity = stock_quantity - reserved_quantity
    - is_low_stock = available_quantity <= min_stock_level
    - stock_status = "out_of_stock" | "low_stock" | "in_stock"
    
    用途:
    - 全ての在庫API応答
    - フロントエンド表示データ
    - SwaggerUI での応答例
    """
    # データベース設定（SQLAlchemy ORM連携）
    model_config = ConfigDict(
        from_attributes=True,  # SQLAlchemyモデルから自動変換
        json_schema_extra={
            "example": {
                "id": 1,
                "sku": "PROD-001",
                "name": "ワイヤレスヘッドホン プレミアム",
                "description": "高音質ノイズキャンセリング機能付きワイヤレスヘッドホン",
                "category": "electronics",
                "stock_quantity": 45,
                "reserved_quantity": 3,
                "available_quantity": 42,
                "weight": 250.0,
                "dimensions": "20cm x 18cm x 8cm",
                "cost_price": 8000.0,
                "min_stock_level": 10,
                "max_stock_level": 200,
                "is_active": True,
                "is_trackable": True,
                "is_low_stock": False,
                "stock_status": "in_stock",
                "created_at": "2024-12-16T00:00:00Z",
                "updated_at": "2024-12-16T02:00:00Z"
            }
        }
    )
    
    # データベース由来フィールド
    id: int = Field(
        ...,
        description="データベース主キー - 一意識別子",
        example=1
    )
    stock_quantity: int = Field(
        ...,
        description="実在庫数 - データベース格納値",
        example=45
    )
    reserved_quantity: int = Field(
        ...,
        description="予約済み数量 - データベース格納値",
        example=3
    )
    available_quantity: int = Field(
        ...,
        description="利用可能数量 - 自動計算値",
        example=42
    )
    
    # タイムスタンプ
    created_at: datetime = Field(
        ...,
        description="作成日時 - ISO8601形式",
        example="2024-12-16T00:00:00Z"
    )
    updated_at: datetime = Field(
        ...,
        description="最終更新日時 - ISO8601形式",
        example="2024-12-16T02:00:00Z"
    )
    
    # 計算プロパティ（ビジネスロジック）
    is_low_stock: bool = Field(
        False,
        description="低在庫フラグ - available_quantity <= min_stock_level",
        example=False
    )
    stock_status: str = Field(
        "in_stock",
        description="在庫ステータス - out_of_stock/low_stock/in_stock",
        example="in_stock"
    )


class InventoryStockAlert(BaseModel):
    """
    在庫アラート用スキーマ
    
    低在庫や在庫切れ時のアラート情報を表現するスキーマです。
    在庫監視システムでの警告表示やアラート処理に使用されます。
    
    アラートレベル:
    - "low": 低在庫（min_stock_level以下）
    - "critical": 危険在庫（min_stock_levelの50%以下）
    - "out_of_stock": 在庫切れ（available_quantity = 0）
    
    計算ロジック:
    - shortage_amount = max(0, min_stock_level - current_stock)
    - alert_level は current_stock と min_stock_level の比較で決定
    
    用途:
    - 低在庫アラート表示
    - 在庫切れ通知
    - ダッシュボード警告表示
    - 自動発注トリガー
    """
    # SQLAlchemy ORM連携設定
    model_config = ConfigDict(from_attributes=True)
    
    # アラート基本情報
    id: int = Field(
        ...,
        description="在庫アイテムID",
        example=1
    )
    sku: str = Field(
        ...,
        description="商品コード（SKU）",
        example="PROD-001"
    )
    name: str = Field(
        ...,
        description="商品名",
        example="ワイヤレスヘッドホン"
    )
    
    # 在庫数量情報
    current_stock: int = Field(
        ...,
        description="現在の利用可能在庫数",
        example=5
    )
    min_stock_level: int = Field(
        ...,
        description="最小在庫レベル（閾値）",
        example=10
    )
    shortage_amount: int = Field(
        ...,
        description="不足数量 - 最小レベルからの差分",
        example=5
    )
    
    # アラート分類
    alert_level: str = Field(
        ...,
        description="アラートレベル - low/critical/out_of_stock",
        example="low"
    )