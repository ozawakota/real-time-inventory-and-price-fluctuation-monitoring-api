# リアルタイム在庫・価格変動監視API バックエンド

## 開発環境セットアップ

### 必須要件
- Python 3.11+
- Docker & Docker Compose
- Git

### セットアップ手順

1. **リポジトリのクローン**
   ```bash
   git clone <repository-url>
   cd real-time-inventory-and-price-fluctuation-monitoring-api/backend
   ```

2. **環境変数の設定**
   ```bash
   cp .env.example .env
   # .envファイルを適切に編集してください
   ```

3. **Python仮想環境の作成**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # または
   venv\Scripts\activate     # Windows
   ```

4. **依存関係のインストール**
   ```bash
   pip install -r requirements.txt
   ```

5. **データベースとRedisの起動**
   ```bash
   # プロジェクトルートディレクトリで実行
   cd ..
   docker-compose up -d postgres redis
   ```

6. **アプリケーションの起動**
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API エンドポイント

### 在庫管理
- `GET /api/v1/inventory/` - 全在庫アイテム取得
- `GET /api/v1/inventory/{item_id}` - 特定アイテム取得
- `POST /api/v1/inventory/` - 新規アイテム作成
- `PUT /api/v1/inventory/{item_id}` - アイテム更新
- `DELETE /api/v1/inventory/{item_id}` - アイテム削除
- `GET /api/v1/inventory/low-stock/alert` - 在庫不足アラート

### 価格管理
- `GET /api/v1/price/` - 全価格情報取得
- `GET /api/v1/price/{item_id}` - 特定アイテムの価格取得
- `POST /api/v1/price/` - 価格作成・更新
- `PUT /api/v1/price/{item_id}` - 価格更新
- `GET /api/v1/price/{item_id}/history` - 価格履歴取得
- `GET /api/v1/price/changes/significant` - 重要な価格変更取得

### WebSocket エンドポイント
- `/ws/inventory` - 在庫更新のリアルタイム通知
- `/ws/price` - 価格更新のリアルタイム通知

## アクセス方法

### API ドキュメント
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### ヘルスチェック
- **Health Check**: http://localhost:8000/health

## アーキテクチャ

```
app/
├── api/v1/          # API ルーティング
│   └── endpoints/   # エンドポイント定義
├── core/           # コア設定
│   ├── config.py   # アプリケーション設定
│   ├── database.py # データベース設定
│   └── redis_client.py # Redis クライアント
├── db/             # データベース関連
├── models/         # SQLAlchemy モデル
├── schemas/        # Pydantic スキーマ
└── services/       # ビジネスロジック
```

## 主要機能

### 🔄 リアルタイム通信
- WebSocket による即座データ配信
- Redis Pub/Sub によるイベント駆動アーキテクチャ
- 在庫・価格変更の自動通知

### 📊 キャッシュ戦略
- Redis による頻繁アクセスデータの高速化
- 適切な TTL 設定によるデータ整合性確保

### ⚠️ アラート機能
- 在庫不足時の自動アラート
- 価格変動閾値による通知システム
- 重要度別のアラート分類

### 🔍 データ整合性
- Pydantic による厳格な型検証
- ビジネスロジック層での整合性チェック
- トランザクション管理

## 開発時の注意事項

### データベース
- PostgreSQL 15 を使用
- 非同期ドライバ (asyncpg) による高性能アクセス
- SQLAlchemy 2.0 の新しい API を使用

### Redis
- キャッシュとメッセージング の両方で使用
- 適切な TTL 設定でメモリ使用量を最適化

### ログ
- 構造化ログ (structlog) による詳細な追跡
- エラーハンドリングと適切なログレベル設定

## テスト

```bash
# テストの実行
pytest

# カバレッジ付きテスト実行
pytest --cov=app tests/
```

## Docker での開発

```bash
# 全サービス起動 (PostgreSQL, Redis, Backend)
docker-compose up

# バックグラウンド起動
docker-compose up -d

# ログ確認
docker-compose logs -f backend

# サービス停止
docker-compose down
```

## API 使用例

### 在庫アイテム作成

```bash
curl -X POST "http://localhost:8000/api/v1/inventory/" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "PROD-001",
    "name": "Premium Wireless Headphones",
    "description": "高品質ノイズキャンセリングワイヤレスヘッドホン",
    "category": "Electronics",
    "stock_quantity": 50,
    "reserved_quantity": 5,
    "cost_price": 8000.0,
    "min_stock_level": 10,
    "max_stock_level": 200
  }'
```

### 価格設定

```bash
curl -X POST "http://localhost:8000/api/v1/price/" \
  -H "Content-Type: application/json" \
  -d '{
    "inventory_id": 1,
    "selling_price": 12000.0,
    "cost_price": 8000.0,
    "discount_price": 10800.0,
    "currency": "JPY"
  }'
```

### WebSocket 接続テスト

```javascript
// JavaScript での WebSocket 接続例
const ws = new WebSocket('ws://localhost:8000/ws/inventory');

ws.onopen = function(event) {
    console.log('WebSocket connected');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onclose = function(event) {
    console.log('WebSocket disconnected');
};
```

## OpenAPI-TS 型定義自動生成

### フロントエンド連携

このAPIは**OpenAPI-TypeScript**を使用してTypeScript型定義を自動生成できます。

#### 1. フロントエンド側の設定

```bash
# frontend ディレクトリで実行
cd ../frontend

# 依存関係のインストール
npm install

# OpenAPIスキーマから型定義を生成
npm run generate-api
```

#### 2. 自動生成される型定義

```typescript
// 生成される型定義例 (src/lib/api/schema.ts)
export interface InventoryResponse {
  id: number;
  sku: string;
  name: string;
  stock_quantity: number;
  available_quantity: number;
  is_low_stock: boolean;
  // ... その他のプロパティ
}

export interface PriceResponse {
  id: number;
  inventory_id: number;
  selling_price: number;
  final_price: number;
  // ... その他のプロパティ
}
```

#### 3. 型安全なAPIクライアントの使用

```typescript
import { apiClient, type InventoryItem } from './src/lib/api/client';

// 型安全なAPI呼び出し
const items: InventoryItem[] = await apiClient.getInventory();

// React Query hooks with type safety
import { useInventoryList, useCreateInventoryItem } from './src/lib/hooks/use-inventory';

function InventoryComponent() {
  const { data: inventory, isLoading } = useInventoryList(0, 50);
  const createMutation = useCreateInventoryItem();

  const handleCreate = async (formData: InventoryCreate) => {
    await createMutation.mutateAsync(formData);
  };

  return (
    // 完全な型安全性でコンポーネントを実装
  );
}
```

#### 4. リアルタイム更新の統合

```typescript
import { useWebSocket, useConnectionStatus } from './src/lib/hooks/use-websocket';

function Dashboard() {
  // 自動的にリアルタイム更新を受信
  const { isConnected } = useWebSocket();
  const { status, statusText } = useConnectionStatus();

  return (
    <div>
      <div className={`status ${statusColor}`}>
        {statusText}
      </div>
      {/* リアルタイム更新されるダッシュボード */}
    </div>
  );
}
```

### NPMスクリプト

フロントエンド側で使用可能なコマンド:

```bash
# API型定義を生成 (FastAPIサーバーが起動している必要があります)
npm run generate-api

# ローカルのOpenAPIファイルから生成
npm run generate-api:local

# バックエンドファイルの変更を監視して自動再生成
npm run generate-api:watch

# ビルド前に自動生成
npm run build
```

### 開発ワークフロー

1. **バックエンドAPI更新** → FastAPIでエンドポイント追加/変更
2. **型定義生成** → `npm run generate-api` で最新スキーマを取得
3. **フロントエンド開発** → 生成された型定義を使用して型安全な開発
4. **リアルタイム更新** → WebSocket hookで自動データ同期

### ファイル構造

```
frontend/
├── src/lib/
│   ├── api/
│   │   ├── schema.ts      # 自動生成される型定義
│   │   └── client.ts      # 型安全なAPIクライアント
│   └── hooks/
│       ├── use-inventory.ts # 在庫管理hooks
│       ├── use-price.ts     # 価格管理hooks
│       └── use-websocket.ts # リアルタイム更新
├── scripts/
│   └── generate-api-types.js # 型定義生成スクリプト
└── package.json           # NPMスクリプト設定
```