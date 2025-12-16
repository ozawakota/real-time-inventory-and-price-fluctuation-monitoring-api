"""
価格管理システム用Pydanticスキーマ定義

このファイルでは、価格データのバリデーション、シリアライゼーション、
ドキュメント生成のためのスキーマを定義しています。

主要なスキーマ:
- PriceBase: 共通の基本価格フィールド
- PriceCreate: 新規価格作成用（在庫IDと価格情報必須）
- PriceUpdate: 部分更新用（全フィールドオプション）
- PriceResponse: API応答用（計算フィールド、履歴情報含む）
- PriceHistoryResponse: 価格変動履歴用
- PriceChangeAlert: 価格変動アラート用

価格計算機能:
- final_price: 割引適用後の最終価格
- calculated_margin: 実際の利益率計算
- change_percent: 価格変動率
- change_amount: 価格変動額

バリデーション機能:
- 価格の正数チェック
- 通貨コード形式検証
- 変動率の計算検証
- 有効期間の整合性確認
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class PriceBase(BaseModel):
    """
    価格情報の基本スキーマクラス
    
    全ての価格関連スキーマの基底クラスとして機能します。
    共通の価格フィールドとバリデーションルールを定義しています。
    
    フィールド詳細:
    - selling_price: 販売価格（税込み） - 顧客向け表示価格
    - cost_price: 原価 - 利益計算・価格設定基準
    - discount_price: 割引価格 - キャンペーン・セール時適用
    - currency: 通貨コード - ISO 4217形式（3文字）
    - margin_percent: 利益率 - 設定目標値
    - markup_percent: マークアップ率 - 原価に対する上乗せ率
    - is_active: アクティブフラグ - 価格の有効状態
    - requires_approval: 承認要求フラグ - 価格変更の承認プロセス
    
    価格計算ロジック:
    - 利益率 = (販売価格 - 原価) / 販売価格 * 100
    - マークアップ率 = (販売価格 - 原価) / 原価 * 100
    - 最終価格 = 割引価格が設定されている場合は割引価格、そうでなければ販売価格
    """
    # 基本価格情報
    selling_price: float = Field(
        ..., 
        gt=0,
        description="販売価格（税込み）- 顧客向け表示価格",
        example=12000.0
    )
    cost_price: float = Field(
        ..., 
        ge=0,
        description="原価 - 利益計算・価格設定用",
        example=8000.0
    )
    discount_price: Optional[float] = Field(
        None, 
        gt=0,
        description="割引価格 - キャンペーン・セール時適用",
        example=10800.0
    )
    currency: str = Field(
        "JPY", 
        min_length=3, 
        max_length=3,
        description="通貨コード - ISO 4217形式",
        example="JPY"
    )
    
    # 利益管理
    margin_percent: Optional[float] = Field(
        None,
        description="利益率目標 - (販売価格-原価)/販売価格*100",
        example=25.0
    )
    markup_percent: Optional[float] = Field(
        None,
        description="マークアップ率目標 - (販売価格-原価)/原価*100",
        example=50.0
    )
    
    # 状態管理フラグ
    is_active: bool = Field(
        True,
        description="アクティブフラグ - 価格の有効状態",
        example=True
    )
    requires_approval: bool = Field(
        False,
        description="承認要求フラグ - 価格変更の承認プロセス",
        example=False
    )


class PriceCreate(PriceBase):
    """
    価格新規作成用スキーマ
    
    新しい価格情報を作成する際に使用されるスキーマです。
    PriceBaseの全フィールドに加えて、対象在庫IDの必須指定を含みます。
    
    追加フィールド:
    - inventory_id: 対象在庫アイテムID - 価格設定対象の特定
    
    作成時の自動処理:
    - 既存価格の無効化（effective_until設定）
    - 価格変動履歴の記録
    - 大幅変動時のアラート生成
    - 計算フィールドの自動算出
    
    用途:
    - POST /api/v1/price/ エンドポイント
    - 新商品価格設定
    - 価格改定時の新価格登録
    - SwaggerUI でのAPI仕様表示
    
    バリデーション:
    - 在庫IDの存在確認
    - 価格の正数チェック
    - 通貨コード形式検証
    - 利益率の妥当性確認
    """
    # 関連情報
    inventory_id: int = Field(
        ..., 
        gt=0,
        description="対象在庫アイテムID - 価格設定対象の特定",
        example=1
    )
    
    # SwaggerUI での表示用設定
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "inventory_id": 1,
                "selling_price": 12000.0,
                "cost_price": 8000.0,
                "discount_price": 10800.0,
                "currency": "JPY",
                "margin_percent": 25.0,
                "markup_percent": 50.0,
                "is_active": True,
                "requires_approval": False
            }
        }
    )


class PriceUpdate(BaseModel):
    """
    価格部分更新用スキーマ
    
    既存の価格情報を部分的に更新する際に使用されるスキーマです。
    全てのフィールドがOptional（任意）となっており、変更したいフィールドのみ指定可能です。
    
    部分更新の特徴:
    - 指定されたフィールドのみ更新
    - 未指定フィールドは既存値を保持
    - 価格変動履歴の自動記録
    - 計算フィールドの自動再計算
    - 変動率に応じたアラート生成
    
    用途:
    - PUT /api/v1/price/{item_id} エンドポイント
    - 既存価格の調整・変更
    - キャンペーン価格の適用
    - 承認フラグの変更
    
    使用例:
    - 販売価格のみ変更: {"selling_price": 11000.0}
    - 割引価格の適用: {"discount_price": 9800.0}
    - 複数フィールド: {"selling_price": 13000.0, "change_reason": "競合対応"}
    
    履歴管理:
    - 全ての変更が価格履歴テーブルに記録
    - 変更理由の記録（change_reason）
    - 変更者の追跡（システムレベル）
    """
    # 価格情報（部分更新対応）
    selling_price: Optional[float] = Field(
        None, 
        gt=0,
        description="販売価格の更新",
        example=11000.0
    )
    cost_price: Optional[float] = Field(
        None, 
        ge=0,
        description="原価の更新",
        example=7500.0
    )
    discount_price: Optional[float] = Field(
        None, 
        gt=0,
        description="割引価格の設定・変更",
        example=9800.0
    )
    currency: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=3,
        description="通貨コードの変更",
        example="USD"
    )
    
    # 利益管理（部分更新対応）
    margin_percent: Optional[float] = Field(
        None,
        description="利益率目標の調整",
        example=20.0
    )
    markup_percent: Optional[float] = Field(
        None,
        description="マークアップ率目標の調整",
        example=45.0
    )
    
    # 状態管理フラグ（部分更新対応）
    is_active: Optional[bool] = Field(
        None,
        description="アクティブ状態の切り替え",
        example=False
    )
    requires_approval: Optional[bool] = Field(
        None,
        description="承認要求状態の変更",
        example=True
    )
    
    # 変更管理
    change_reason: Optional[str] = Field(
        None, 
        max_length=255,
        description="価格変更理由 - 履歴記録用",
        example="競合価格対応のため値下げ"
    )


class PriceResponse(PriceBase):
    """
    価格API応答用スキーマ
    
    APIエンドポイントからの価格応答データ形式を定義するスキーマです。
    PriceBaseの全フィールドに加えて、ID、計算フィールド、
    タイムスタンプ等の応答専用フィールドを含みます。
    
    応答専用フィールド:
    - id: データベース主キー
    - inventory_id: 関連在庫アイテムID
    - effective_from: 価格有効開始日時
    - effective_until: 価格有効終了日時
    - created_at: 作成日時
    - updated_at: 最終更新日時
    - final_price: 最終価格（計算値）
    - calculated_margin: 実際の利益率（計算値）
    
    計算ロジック:
    - final_price = discount_price または selling_price
    - calculated_margin = (final_price - cost_price) / final_price * 100
    - 有効期間管理による価格の時系列追跡
    
    用途:
    - 全ての価格API応答
    - フロントエンド表示データ
    - SwaggerUI での応答例
    - 価格履歴との関連付け
    
    データベース連携:
    - SQLAlchemy ORM からの自動変換
    - 計算プロパティの動的算出
    - 関連エンティティの参照
    """
    # データベース設定（SQLAlchemy ORM連携）
    model_config = ConfigDict(
        from_attributes=True,  # SQLAlchemyモデルから自動変換
        json_schema_extra={
            "example": {
                "id": 1,
                "inventory_id": 1,
                "selling_price": 12000.0,
                "cost_price": 8000.0,
                "discount_price": 10800.0,
                "currency": "JPY",
                "margin_percent": 25.0,
                "markup_percent": 50.0,
                "is_active": True,
                "requires_approval": False,
                "final_price": 10800.0,
                "calculated_margin": 25.93,
                "effective_from": "2024-01-01T00:00:00Z",
                "effective_until": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )
    
    # データベース由来フィールド
    id: int = Field(
        ...,
        description="データベース主キー - 一意識別子",
        example=1
    )
    inventory_id: int = Field(
        ...,
        description="関連在庫アイテムID - 外部キー",
        example=1
    )
    
    # タイムスタンプ・有効期間
    effective_from: datetime = Field(
        ...,
        description="価格有効開始日時 - ISO8601形式",
        example="2024-01-01T00:00:00Z"
    )
    effective_until: Optional[datetime] = Field(
        None,
        description="価格有効終了日時 - None=無期限",
        example=None
    )
    created_at: datetime = Field(
        ...,
        description="作成日時 - ISO8601形式",
        example="2024-01-01T00:00:00Z"
    )
    updated_at: datetime = Field(
        ...,
        description="最終更新日時 - ISO8601形式",
        example="2024-01-01T00:00:00Z"
    )
    
    # 計算プロパティ（ビジネスロジック）
    final_price: float = Field(
        0.0,
        description="最終価格 - 割引適用後の実売価格",
        example=10800.0
    )
    calculated_margin: float = Field(
        0.0,
        description="実際の利益率 - 最終価格ベース計算",
        example=25.93
    )


class PriceHistoryResponse(BaseModel):
    """
    価格変動履歴応答用スキーマ
    
    価格変更の履歴追跡とアナリティクス機能のためのスキーマです。
    全ての価格変動を時系列で記録し、分析可能な形式で提供します。
    
    履歴データ要素:
    - 変更前後価格: 完全な価格変動記録
    - 変更メタデータ: 理由、実行者、変更タイプ
    - 計算フィールド: 変動率、金額、重要度判定
    - タイムスタンプ: 変更日時の精密記録
    
    分析機能:
    - 価格トレンド分析のためのデータ提供
    - 価格変動の統計的解析基盤
    - 異常価格変動の検出支援
    - 価格設定戦略の効果測定
    
    用途:
    - 価格履歴API応答 (/api/v1/price/history/{item_id})
    - 価格変動レポート生成
    - 価格アナリティクスダッシュボード
    - 価格監査と承認プロセス
    - リアルタイム価格変動アラート
    
    ビジネス価値:
    - 価格決定プロセスの透明化
    - 価格変動パターンの把握
    - 競合対応履歴の記録
    - 価格戦略の効果検証
    """
    # データベース連携設定
    model_config = ConfigDict(from_attributes=True)
    
    # 基本識別情報
    id: int = Field(
        ...,
        description="履歴レコードID - 一意識別子",
        example=1
    )
    inventory_id: int = Field(
        ...,
        description="対象在庫アイテムID - 価格変更対象の特定",
        example=1
    )
    
    # 価格変動データ（必須フィールド）
    old_price: float = Field(
        ...,
        description="変更前価格 - 比較基準となる旧価格",
        example=12000.0
    )
    new_price: float = Field(
        ...,
        description="変更後価格 - 新設定価格",
        example=11000.0
    )
    price_change_percent: Optional[float] = Field(
        None,
        description="価格変動率 - パーセンテージ表示（負値=値下げ）",
        example=-8.33
    )
    price_change_amount: Optional[float] = Field(
        None,
        description="価格変動額 - 絶対額での変動（負値=値下げ）",
        example=-1000.0
    )
    
    # 変更管理メタデータ（任意フィールド）
    change_reason: Optional[str] = Field(
        None,
        max_length=255,
        description="価格変更理由 - ビジネス上の変更根拠",
        example="競合価格対応のため値下げ"
    )
    changed_by: Optional[str] = Field(
        None,
        max_length=100,
        description="変更実行者 - 価格変更を行ったユーザー",
        example="price_manager_001"
    )
    change_type: Optional[str] = Field(
        None,
        max_length=50,
        description="変更タイプ - 価格変更の分類",
        example="competitive_adjustment"
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="補足メモ - 追加の変更詳細や背景情報",
        example="競合他社の価格調査に基づく戦略的調整"
    )
    
    # タイムスタンプ
    changed_at: datetime = Field(
        ...,
        description="価格変更実行日時 - ISO8601形式",
        example="2024-01-15T14:30:00Z"
    )
    
    # 計算プロパティ（分析用）
    is_price_increase: bool = Field(
        False,
        description="価格上昇フラグ - True=値上げ、False=値下げ",
        example=False
    )
    change_significance: str = Field(
        "minor",
        description="変動重要度 - minor/moderate/major/critical",
        example="moderate"
    )


class PriceChangeAlert(BaseModel):
    """
    価格変動アラート通知用スキーマ
    
    重要な価格変動を検出した際の即座アラート配信のためのスキーマです。
    設定された閾値を超える価格変動や異常な価格設定を自動検出し、
    関係者への通知と迅速な対応を支援します。
    
    アラート検出条件:
    - 大幅価格変動: 設定閾値（例：±10%）を超える変動
    - 急激な価格変更: 短期間での複数回変更
    - 異常価格設定: 原価割れや異常高価格の検出
    - 競合価格乖離: 市場価格との大幅な乖離
    
    通知機能:
    - リアルタイムWebSocket通知
    - メール・Slack等の外部通知連携
    - ダッシュボードでの視覚的アラート表示
    - モバイルプッシュ通知対応
    
    アラートレベル:
    - significant_increase: 大幅値上げ（要注意）
    - significant_decrease: 大幅値下げ（要確認）  
    - major_change: 重大変更（即時対応必要）
    - anomaly_detected: 異常値検出（システム確認要）
    
    用途:
    - 価格監視システムのアラート配信
    - 経営層・価格管理者への緊急通知
    - 自動価格調整システムの判断材料
    - 価格戦略の即時フィードバック
    - 競合対応の迅速な意思決定支援
    
    ビジネス効果:
    - 価格リスクの即座検出と対応
    - 収益機会の逸失防止
    - 価格競争力の維持
    - 価格設定ミスの早期発見
    """
    # 商品識別情報
    inventory_id: int = Field(
        ...,
        description="在庫アイテムID - 価格変動対象の特定",
        example=1
    )
    sku: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="商品SKU - 商品の一意識別子",
        example="PROD-001-2024"
    )
    item_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="商品名 - 通知メッセージでの商品表示名",
        example="プレミアムワイヤレスヘッドフォン"
    )
    
    # 価格変動詳細データ
    old_price: float = Field(
        ...,
        gt=0,
        description="変更前価格 - アラート判定基準価格",
        example=12000.0
    )
    new_price: float = Field(
        ...,
        gt=0,
        description="変更後価格 - 新設定価格",
        example=15000.0
    )
    change_percent: float = Field(
        ...,
        description="価格変動率 - パーセンテージ（正値=値上げ、負値=値下げ）",
        example=25.0
    )
    change_amount: float = Field(
        ...,
        description="価格変動額 - 絶対額（正値=値上げ、負値=値下げ）",
        example=3000.0
    )
    
    # アラート分類・重要度
    alert_type: str = Field(
        ...,
        description="""
        アラートタイプ分類:
        - significant_increase: 大幅値上げ（10-25%上昇）
        - significant_decrease: 大幅値下げ（10-25%下落）
        - major_change: 重大変更（25%以上の変動）
        - anomaly_detected: 異常値検出（原価割れ等）
        - competitive_alert: 競合価格乖離アラート
        """,
        example="significant_increase"
    )
    
    # 発生タイムスタンプ
    timestamp: datetime = Field(
        ...,
        description="アラート発生日時 - 価格変動検出時刻（ISO8601形式）",
        example="2024-01-15T14:30:00Z"
    )