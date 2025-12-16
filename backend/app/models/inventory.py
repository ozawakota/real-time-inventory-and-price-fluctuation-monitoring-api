"""
在庫管理データベースモデル

このファイルでは、在庫管理システムのデータベーススキーマを定義しています。
SQLAlchemyのORMを使用してテーブル構造、インデックス、制約を定義し、
ビジネスロジックプロパティも含んでいます。

データベース設計原則:
- 正規化（第3正規形）
- インデックス最適化
- 制約による整合性保証
- タイムスタンプ自動管理
- 計算プロパティによる動的データ

テーブル: inventory
主要用途:
- 商品情報管理
- 在庫数量追跡
- 価格・コスト管理
- アラート閾値設定
- 状態・履歴管理
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class Inventory(Base):
    """
    在庫アイテムデータベースモデル
    
    在庫管理システムの中核となるテーブルモデルです。
    商品情報、在庫数量、価格、物理的特性、ビジネスルール等を管理します。
    
    テーブル設計:
    - 主キー: id (自動インクリメント)
    - ユニークキー: sku (商品コード)
    - インデックス: id, sku, category
    - 制約: NOT NULL, UNIQUE, DEFAULT値
    
    計算フィールド:
    - available_quantity = stock_quantity - reserved_quantity
    - is_low_stock = available_quantity <= min_stock_level
    - stock_status = out_of_stock | low_stock | in_stock
    
    リレーション:
    - (将来拡張) price_history: 価格履歴
    - (将来拡張) stock_movements: 在庫移動履歴
    - (将来拡張) suppliers: 仕入先情報
    """
    __tablename__ = "inventory"

    # === 主キー・識別子 ===
    id = Column(
        Integer, 
        primary_key=True, 
        index=True,
        comment="在庫アイテムID - 主キー"
    )
    sku = Column(
        String(100), 
        unique=True, 
        index=True, 
        nullable=False,
        comment="商品コード（SKU）- ユニーク制約、高速検索用インデックス"
    )
    
    # === 商品基本情報 ===
    name = Column(
        String(255), 
        nullable=False,
        comment="商品名 - 表示用正式名称"
    )
    description = Column(
        Text,
        comment="商品説明 - 詳細情報（オプション）"
    )
    category = Column(
        String(100), 
        index=True,
        comment="カテゴリ - 分類用、検索インデックス付き"
    )
    
    # === 在庫数量情報 ===
    stock_quantity = Column(
        Integer, 
        nullable=False, 
        default=0,
        comment="実在庫数 - 物理的に存在する商品数量"
    )
    reserved_quantity = Column(
        Integer, 
        nullable=False, 
        default=0,
        comment="予約済み数量 - 注文済みだが未出荷の数量"
    )
    available_quantity = Column(
        Integer, 
        nullable=False, 
        default=0,
        comment="利用可能数量 - stock_quantity - reserved_quantity（計算値）"
    )
    
    # === 物理的特性 ===
    weight = Column(
        Float,
        comment="重量（グラム単位）- 配送コスト計算用"
    )
    dimensions = Column(
        String(100),
        comment="寸法 - 'length x width x height' 形式"
    )
    
    # === ビジネス属性 ===
    cost_price = Column(
        Float, 
        nullable=False, 
        default=0.0,
        comment="原価 - 利益計算・価格設定基準"
    )
    min_stock_level = Column(
        Integer, 
        nullable=False, 
        default=10,
        comment="最小在庫レベル - 低在庫アラート閾値"
    )
    max_stock_level = Column(
        Integer, 
        nullable=False, 
        default=1000,
        comment="最大在庫レベル - 過剰在庫防止"
    )
    
    # === 状態管理フラグ ===
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="アクティブフラグ - 販売可能状態"
    )
    is_trackable = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="追跡可能フラグ - 在庫管理対象かどうか"
    )
    
    # === タイムスタンプ（自動管理） ===
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="作成日時 - レコード作成時に自動設定"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="更新日時 - レコード更新時に自動更新"
    )
    
    def __repr__(self):
        """
        オブジェクト文字列表現
        
        デバッグやログ出力時の識別用文字列を生成します。
        主要な識別情報（ID、SKU、在庫数）を含みます。
        
        Returns:
            str: "<Inventory(id=1, sku='PROD-001', stock=50)>" 形式
        """
        return f"<Inventory(id={self.id}, sku='{self.sku}', stock={self.stock_quantity})>"
    
    @property
    def is_low_stock(self) -> bool:
        """
        低在庫判定プロパティ
        
        利用可能在庫数が最小在庫レベル以下かどうかを判定します。
        アラート表示やダッシュボードの警告表示に使用されます。
        
        判定ロジック:
        available_quantity <= min_stock_level
        
        Returns:
            bool: True=低在庫状態, False=正常在庫
            
        Use Cases:
        - 低在庫アラート表示
        - ダッシュボード警告マーク
        - 自動発注トリガー
        - レポート集計
        """
        return self.available_quantity <= self.min_stock_level
    
    @property
    def stock_status(self) -> str:
        """
        在庫ステータス文字列プロパティ
        
        現在の在庫状況を3段階で分類した文字列を返します。
        フロントエンドでの色分け表示やフィルタリングに使用されます。
        
        ステータス分類:
        - "out_of_stock": 在庫切れ（available_quantity = 0）
        - "low_stock": 低在庫（0 < available_quantity <= min_stock_level）
        - "in_stock": 正常在庫（available_quantity > min_stock_level）
        
        Returns:
            str: 在庫ステータス文字列
            
        UI表示例:
        - out_of_stock → 赤色表示
        - low_stock → オレンジ色表示
        - in_stock → 緑色表示
        """
        if self.available_quantity <= 0:
            return "out_of_stock"
        elif self.is_low_stock:
            return "low_stock"
        else:
            return "in_stock"