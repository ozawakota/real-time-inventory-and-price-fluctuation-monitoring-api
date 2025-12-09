# 📡 FastAPI 実践ガイド - API操作とリアルタイム通信

## 📖 目次

1. [API基本操作](#api基本操作)
2. [在庫管理API](#在庫管理api)
3. [価格管理API](#価格管理api)
4. [リアルタイム通信](#リアルタイム通信)
5. [エラーハンドリング](#エラーハンドリング)
6. [実践シナリオ](#実践シナリオ)
7. [パフォーマンス最適化](#パフォーマンス最適化)

---

## 🚀 API基本操作

### 📋 開発環境のアクセス先

| サービス | URL | 用途 |
|---------|-----|------|
| **API サーバー** | `http://localhost:8000` | メインAPI |
| **Swagger UI** | `http://localhost:8000/docs` | インタラクティブAPIドキュメント |
| **ReDoc** | `http://localhost:8000/redoc` | 読みやすいAPIリファレンス |
| **ヘルスチェック** | `http://localhost:8000/health` | サーバー稼働状況 |

### 🔧 基本的なHTTPメソッド

```bash
# GET - データ取得
curl http://localhost:8000/api/v1/inventory/

# POST - データ作成
curl -X POST http://localhost:8000/api/v1/inventory/ \
  -H "Content-Type: application/json" \
  -d '{"sku":"TEST-001","name":"テスト商品",...}'

# PUT - データ更新
curl -X PUT http://localhost:8000/api/v1/inventory/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"更新されたテスト商品",...}'

# DELETE - データ削除
curl -X DELETE http://localhost:8000/api/v1/inventory/1
```

### 📊 レスポンス形式

#### 成功レスポンス
```json
{
  "id": 1,
  "sku": "TEST-001",
  "name": "テスト商品",
  "stock_quantity": 50,
  "available_quantity": 45,
  "created_at": "2025-12-09T04:19:39.525844Z",
  "updated_at": "2025-12-09T04:19:39.525844Z"
}
```

#### エラーレスポンス
```json
{
  "detail": "Inventory item not found",
  "status_code": 404,
  "timestamp": "2025-12-09T04:19:39.525844Z"
}
```

---

## 📦 在庫管理API

### 🗂️ エンドポイント一覧

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| `GET` | `/api/v1/inventory/` | 在庫一覧取得 |
| `POST` | `/api/v1/inventory/` | 新規在庫作成 |
| `GET` | `/api/v1/inventory/{id}` | 特定在庫取得 |
| `PUT` | `/api/v1/inventory/{id}` | 在庫更新 |
| `DELETE` | `/api/v1/inventory/{id}` | 在庫削除 |
| `GET` | `/api/v1/inventory/low-stock/alert` | 在庫不足アラート |

### 📝 実践例: 在庫管理フロー

#### 1. 新規商品の登録

**リクエスト:**
```bash
curl -X POST http://localhost:8000/api/v1/inventory/ \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "LAPTOP-001",
    "name": "ゲーミングノートPC",
    "description": "高性能ゲーミング向けノートパソコン RTX 4070搭載",
    "category": "Electronics",
    "stock_quantity": 25,
    "reserved_quantity": 3,
    "weight": 2800.0,
    "dimensions": "35cm x 25cm x 2.5cm",
    "cost_price": 180000.0,
    "min_stock_level": 5,
    "max_stock_level": 100,
    "is_active": true,
    "is_trackable": true
  }'
```

**レスポンス例:**
```json
{
  "id": 2,
  "sku": "LAPTOP-001",
  "name": "ゲーミングノートPC",
  "description": "高性能ゲーミング向けノートパソコン RTX 4070搭載",
  "category": "Electronics",
  "stock_quantity": 25,
  "reserved_quantity": 3,
  "available_quantity": 22,
  "weight": 2800.0,
  "dimensions": "35cm x 25cm x 2.5cm",
  "cost_price": 180000.0,
  "min_stock_level": 5,
  "max_stock_level": 100,
  "is_active": true,
  "is_trackable": true,
  "created_at": "2025-12-09T05:00:00.000000Z",
  "updated_at": "2025-12-09T05:00:00.000000Z",
  "is_low_stock": false,
  "stock_status": "in_stock"
}
```

#### 2. 在庫検索とフィルタリング

```bash
# 全在庫取得
curl "http://localhost:8000/api/v1/inventory/"

# ページング付き取得
curl "http://localhost:8000/api/v1/inventory/?skip=0&limit=10"

# カテゴリフィルター (TODO: 実装予定)
curl "http://localhost:8000/api/v1/inventory/?category=Electronics"
```

#### 3. 在庫更新（売上処理など）

```bash
# 在庫数量の更新
curl -X PUT http://localhost:8000/api/v1/inventory/2 \
  -H "Content-Type: application/json" \
  -d '{
    "stock_quantity": 22,
    "reserved_quantity": 2
  }'
```

#### 4. 在庫不足アラートの確認

```bash
# 在庫不足商品のチェック
curl http://localhost:8000/api/v1/inventory/low-stock/alert

# アラート例:
# [
#   {
#     "id": 3,
#     "sku": "MOUSE-001",
#     "name": "ワイヤレスマウス",
#     "current_stock": 3,
#     "min_stock_level": 10,
#     "shortage_amount": 7,
#     "alert_level": "low"
#   }
# ]
```

### 🔍 データ検証ルール

#### 必須フィールド
- `sku`: 商品コード（ユニーク、1-100文字）
- `name`: 商品名（1-255文字）
- `cost_price`: 原価（0以上）

#### 自動計算フィールド
- `available_quantity`: `stock_quantity - reserved_quantity`
- `is_low_stock`: `available_quantity <= min_stock_level`
- `stock_status`: 在庫状況（"in_stock", "low_stock", "out_of_stock"）

#### バリデーション例
```bash
# エラー例: SKUが重複
curl -X POST http://localhost:8000/api/v1/inventory/ \
  -H "Content-Type: application/json" \
  -d '{"sku":"LAPTOP-001","name":"重複商品"}'

# エラーレスポンス:
# {
#   "detail": "SKU already exists",
#   "status_code": 400
# }
```

---

## 💰 価格管理API

### 🗂️ エンドポイント一覧

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| `GET` | `/api/v1/price/` | 価格一覧取得 |
| `POST` | `/api/v1/price/` | 価格作成・更新 |
| `GET` | `/api/v1/price/{item_id}` | 特定商品価格取得 |
| `PUT` | `/api/v1/price/{item_id}` | 価格更新 |
| `GET` | `/api/v1/price/{item_id}/history` | 価格履歴取得 |
| `GET` | `/api/v1/price/changes/significant` | 重要な価格変更取得 |

### 📝 実践例: 価格管理フロー

#### 1. 商品価格の設定

```bash
# 新規価格設定
curl -X POST http://localhost:8000/api/v1/price/ \
  -H "Content-Type: application/json" \
  -d '{
    "inventory_id": 2,
    "selling_price": 250000.0,
    "cost_price": 180000.0,
    "discount_price": 230000.0,
    "currency": "JPY",
    "margin_percent": 30.0,
    "markup_percent": 38.89,
    "is_active": true,
    "requires_approval": false
  }'
```

**レスポンス例:**
```json
{
  "id": 2,
  "inventory_id": 2,
  "selling_price": 250000.0,
  "cost_price": 180000.0,
  "discount_price": 230000.0,
  "currency": "JPY",
  "margin_percent": 30.0,
  "markup_percent": 38.89,
  "is_active": true,
  "requires_approval": false,
  "effective_from": "2025-12-09T05:10:00.000000Z",
  "effective_until": null,
  "created_at": "2025-12-09T05:10:00.000000Z",
  "updated_at": "2025-12-09T05:10:00.000000Z",
  "final_price": 230000.0,
  "calculated_margin": 21.74
}
```

#### 2. 価格変更（割引キャンペーンなど）

```bash
# 期間限定割引の設定
curl -X PUT http://localhost:8000/api/v1/price/2 \
  -H "Content-Type: application/json" \
  -d '{
    "discount_price": 200000.0,
    "change_reason": "年末セール価格"
  }'
```

#### 3. 価格履歴の確認

```bash
# 特定商品の価格変更履歴
curl http://localhost:8000/api/v1/price/2/history

# 履歴例:
# [
#   {
#     "id": 1,
#     "inventory_id": 2,
#     "old_price": 230000.0,
#     "new_price": 200000.0,
#     "price_change_percent": -13.04,
#     "price_change_amount": -30000.0,
#     "change_reason": "年末セール価格",
#     "changed_by": "system",
#     "change_type": "discount_update",
#     "changed_at": "2025-12-09T05:15:00.000000Z",
#     "is_price_increase": false,
#     "change_significance": "significant"
#   }
# ]
```

#### 4. 重要な価格変更の監視

```bash
# 大幅な価格変更のアラート確認
curl http://localhost:8000/api/v1/price/changes/significant

# アラート例:
# [
#   {
#     "inventory_id": 2,
#     "sku": "LAPTOP-001",
#     "item_name": "ゲーミングノートPC",
#     "old_price": 230000.0,
#     "new_price": 200000.0,
#     "change_percent": -13.04,
#     "change_amount": -30000.0,
#     "alert_type": "significant_decrease",
#     "timestamp": "2025-12-09T05:15:00.000000Z"
#   }
# ]
```

### 💡 価格計算ロジック

#### 自動計算フィールド
- `final_price`: `discount_price` または `selling_price`
- `calculated_margin`: `((final_price - cost_price) / final_price) * 100`
- `price_change_percent`: `((new_price - old_price) / old_price) * 100`

#### 価格変更しきい値
- **軽微な変更**: 5%未満
- **重要な変更**: 5%以上15%未満  
- **重大な変更**: 15%以上

---

## 🔌 リアルタイム通信

### 🌐 WebSocket エンドポイント

| エンドポイント | 説明 | メッセージタイプ |
|---------------|------|-----------------|
| `/ws/inventory` | 在庫更新通知 | 在庫変更、新規追加、削除 |
| `/ws/price` | 価格更新通知 | 価格変更、割引適用 |

### 📡 実践例: リアルタイム監視

#### 1. JavaScript での WebSocket 接続

```javascript
// 在庫監視用WebSocket接続
const inventorySocket = new WebSocket('ws://localhost:8000/ws/inventory');

inventorySocket.onopen = function(event) {
    console.log('✅ 在庫監視接続開始');
};

inventorySocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('📦 在庫更新:', data);
    
    // UI更新処理
    updateInventoryDisplay(data);
};

inventorySocket.onclose = function(event) {
    console.log('🔌 在庫監視接続終了');
    // 自動再接続ロジック
    setTimeout(() => {
        reconnectWebSocket();
    }, 5000);
};

// 価格監視用WebSocket接続
const priceSocket = new WebSocket('ws://localhost:8000/ws/price');

priceSocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('💰 価格更新:', data);
    
    // 価格アラート表示
    if (data.change_percent > 10) {
        showPriceAlert(data);
    }
};
```

#### 2. Python での WebSocket 接続

```python
import asyncio
import websockets
import json

async def monitor_inventory():
    uri = "ws://localhost:8000/ws/inventory"
    
    async with websockets.connect(uri) as websocket:
        print("✅ 在庫監視開始")
        
        async for message in websocket:
            data = json.loads(message)
            
            print(f"📦 在庫更新: {data['sku']} - {data['message_type']}")
            
            # 在庫不足アラート処理
            if data.get('is_low_stock'):
                print(f"⚠️ 在庫不足アラート: {data['sku']}")
                await send_alert_email(data)

async def monitor_price():
    uri = "ws://localhost:8000/ws/price"
    
    async with websockets.connect(uri) as websocket:
        print("✅ 価格監視開始")
        
        async for message in websocket:
            data = json.loads(message)
            
            print(f"💰 価格更新: {data['sku']} - ¥{data['new_price']}")
            
            # 大幅価格変更アラート
            if abs(data.get('change_percent', 0)) > 15:
                print(f"🚨 大幅価格変更: {data['sku']} ({data['change_percent']:.1f}%)")

# 並行監視実行
async def main():
    await asyncio.gather(
        monitor_inventory(),
        monitor_price()
    )

# 実行
asyncio.run(main())
```

### 📨 WebSocket メッセージ形式

#### 在庫更新メッセージ
```json
{
  "message_type": "inventory_update",
  "action": "updated",
  "item_id": 2,
  "sku": "LAPTOP-001",
  "name": "ゲーミングノートPC",
  "old_quantity": 25,
  "new_quantity": 22,
  "available_quantity": 19,
  "is_low_stock": false,
  "timestamp": "2025-12-09T05:20:00.000000Z"
}
```

#### 価格更新メッセージ
```json
{
  "message_type": "price_update",
  "action": "price_changed",
  "item_id": 2,
  "sku": "LAPTOP-001",
  "name": "ゲーミングノートPC",
  "old_price": 230000.0,
  "new_price": 200000.0,
  "change_percent": -13.04,
  "change_reason": "年末セール価格",
  "timestamp": "2025-12-09T05:15:00.000000Z"
}
```

---

## ❌ エラーハンドリング

### 🚨 HTTPステータスコード

| コード | 説明 | 対処法 |
|--------|------|--------|
| `200` | 成功 | - |
| `201` | 作成成功 | - |
| `400` | 入力データエラー | リクエスト内容を確認 |
| `404` | データが見つからない | IDや検索条件を確認 |
| `409` | 重複エラー | SKUなどユニーク制約を確認 |
| `422` | バリデーションエラー | 入力形式を確認 |
| `500` | サーバーエラー | サーバーログを確認 |

### 🔍 エラー詳細例

#### バリデーションエラー（422）
```bash
curl -X POST http://localhost:8000/api/v1/inventory/ \
  -H "Content-Type: application/json" \
  -d '{"sku":"","name":"","cost_price":-100}'

# レスポンス:
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "sku"],
      "msg": "String should have at least 1 character"
    },
    {
      "type": "string_too_short", 
      "loc": ["body", "name"],
      "msg": "String should have at least 1 character"
    },
    {
      "type": "greater_than_equal",
      "loc": ["body", "cost_price"],
      "msg": "Input should be greater than or equal to 0"
    }
  ]
}
```

#### 存在しないリソース（404）
```bash
curl http://localhost:8000/api/v1/inventory/999

# レスポンス:
{
  "detail": "Inventory item not found",
  "status_code": 404,
  "timestamp": "2025-12-09T05:25:00.000000Z"
}
```

### 🛠️ エラー対処パターン

#### 1. 入力データの検証
```bash
# 事前チェック用のバリデーション関数例
validate_inventory_data() {
    local sku="$1"
    local name="$2"
    local cost_price="$3"
    
    # SKU長さチェック
    if [[ ${#sku} -lt 1 || ${#sku} -gt 100 ]]; then
        echo "エラー: SKUは1-100文字である必要があります"
        return 1
    fi
    
    # 価格チェック  
    if (( $(echo "$cost_price < 0" | bc -l) )); then
        echo "エラー: 原価は0以上である必要があります"
        return 1
    fi
    
    echo "✅ データ検証OK"
    return 0
}
```

#### 2. 重複チェック
```bash
# SKU重複チェック
check_sku_exists() {
    local sku="$1"
    local response=$(curl -s "http://localhost:8000/api/v1/inventory/?sku=$sku")
    
    if [[ $(echo "$response" | jq length) -gt 0 ]]; then
        echo "⚠️ SKU '$sku' は既に存在します"
        return 1
    fi
    
    echo "✅ SKU利用可能"
    return 0
}
```

---

## 🎯 実践シナリオ

### 📦 シナリオ1: ECサイトでの在庫管理

#### 状況設定
オンラインストアで複数商品の在庫を管理し、リアルタイムで在庫状況を監視する。

#### 実装手順

**1. 商品マスタの作成**
```bash
# スマートフォン
curl -X POST http://localhost:8000/api/v1/inventory/ \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "PHONE-001",
    "name": "iPhone 15 Pro",
    "category": "Electronics",
    "stock_quantity": 15,
    "min_stock_level": 5,
    "cost_price": 120000.0
  }'

# ワイヤレスイヤホン
curl -X POST http://localhost:8000/api/v1/inventory/ \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "EARPHONE-001", 
    "name": "AirPods Pro",
    "category": "Electronics",
    "stock_quantity": 30,
    "min_stock_level": 10,
    "cost_price": 25000.0
  }'
```

**2. 価格設定**
```bash
# iPhone価格設定
curl -X POST http://localhost:8000/api/v1/price/ \
  -H "Content-Type: application/json" \
  -d '{
    "inventory_id": 3,
    "selling_price": 159800.0,
    "cost_price": 120000.0,
    "currency": "JPY"
  }'

# AirPods価格設定  
curl -X POST http://localhost:8000/api/v1/price/ \
  -H "Content-Type: application/json" \
  -d '{
    "inventory_id": 4,
    "selling_price": 39800.0,
    "cost_price": 25000.0,
    "currency": "JPY"
  }'
```

**3. 売上処理シミュレーション**
```bash
# iPhone 3台売上
curl -X PUT http://localhost:8000/api/v1/inventory/3 \
  -H "Content-Type: application/json" \
  -d '{"stock_quantity": 12}'

# AirPods 8台売上
curl -X PUT http://localhost:8000/api/v1/inventory/4 \
  -H "Content-Type: application/json" \
  -d '{"stock_quantity": 22}'
```

**4. 在庫不足アラート確認**
```bash
curl http://localhost:8000/api/v1/inventory/low-stock/alert
```

### 💰 シナリオ2: 動的価格調整システム

#### 状況設定
需要に応じて価格を調整し、価格変更履歴を追跡する。

#### 実装手順

**1. セール価格の適用**
```bash
# iPhoneセール価格（10%割引）
curl -X PUT http://localhost:8000/api/v1/price/3 \
  -H "Content-Type: application/json" \
  -d '{
    "discount_price": 143820.0,
    "change_reason": "ブラックフライデーセール"
  }'
```

**2. 競合対応価格変更**
```bash
# AirPods競合対応価格
curl -X PUT http://localhost:8000/api/v1/price/4 \
  -H "Content-Type: application/json" \
  -d '{
    "selling_price": 35800.0,
    "change_reason": "競合価格対応"
  }'
```

**3. 価格変更履歴の分析**
```bash
# iPhone価格履歴
curl http://localhost:8000/api/v1/price/3/history

# 重要な価格変更確認
curl http://localhost:8000/api/v1/price/changes/significant
```

### 🔔 シナリオ3: リアルタイム監視ダッシュボード

#### WebSocketを活用したリアルタイム更新

**1. 監視スクリプトの作成**
```bash
# monitoring_dashboard.py
cat > monitoring_dashboard.py << 'EOF'
import asyncio
import websockets
import json
from datetime import datetime

class InventoryMonitor:
    def __init__(self):
        self.inventory_data = {}
        self.price_data = {}
        
    async def monitor_inventory(self):
        uri = "ws://localhost:8000/ws/inventory"
        async with websockets.connect(uri) as websocket:
            print("📦 在庫監視開始...")
            async for message in websocket:
                data = json.loads(message)
                await self.handle_inventory_update(data)
                
    async def monitor_price(self):
        uri = "ws://localhost:8000/ws/price" 
        async with websockets.connect(uri) as websocket:
            print("💰 価格監視開始...")
            async for message in websocket:
                data = json.loads(message)
                await self.handle_price_update(data)
                
    async def handle_inventory_update(self, data):
        timestamp = datetime.now().strftime("%H:%M:%S")
        sku = data.get('sku', 'UNKNOWN')
        
        if data.get('is_low_stock'):
            print(f"🚨 [{timestamp}] 在庫不足アラート: {sku}")
        else:
            print(f"📦 [{timestamp}] 在庫更新: {sku} -> {data.get('new_quantity')}個")
            
    async def handle_price_update(self, data):
        timestamp = datetime.now().strftime("%H:%M:%S")
        sku = data.get('sku', 'UNKNOWN')
        change_percent = data.get('change_percent', 0)
        
        if abs(change_percent) > 10:
            print(f"⚡ [{timestamp}] 大幅価格変更: {sku} ({change_percent:+.1f}%)")
        else:
            print(f"💰 [{timestamp}] 価格更新: {sku} -> ¥{data.get('new_price'):,}")

    async def run(self):
        await asyncio.gather(
            self.monitor_inventory(),
            self.monitor_price()
        )

# 実行
monitor = InventoryMonitor()
asyncio.run(monitor.run())
EOF

# 実行
python monitoring_dashboard.py
```

---

## ⚡ パフォーマンス最適化

### 📊 Redis キャッシュ活用

#### キャッシュされるデータ
- 在庫一覧（TTL: 5分）
- 商品詳細（TTL: 10分）  
- 価格情報（TTL: 3分）

#### キャッシュ確認コマンド
```bash
# Redis接続
docker exec -it backend-redis-1 redis-cli

# キャッシュ内容確認
KEYS inventory:*
KEYS price:*

# 特定キーの内容確認
GET inventory:list:0:10
```

### 🚀 API パフォーマンス監視

#### レスポンス時間測定
```bash
# 在庫一覧取得の所要時間計測
time curl -s http://localhost:8000/api/v1/inventory/ > /dev/null

# 複数回実行して平均時間を確認
for i in {1..10}; do
    time curl -s http://localhost:8000/api/v1/inventory/ > /dev/null
done
```

#### 同時接続負荷テスト
```bash
# Apache Benchを使用した負荷テスト
ab -n 1000 -c 10 http://localhost:8000/api/v1/inventory/

# 結果例:
# Requests per second: 850.23 [#/sec]
# Time per request: 11.762 [ms]
```

### 🔧 最適化のベストプラクティス

#### 1. データベースクエリ最適化
- インデックス活用（SKU、カテゴリなど）
- ページング実装（大量データ対応）
- 不要なJOINの削除

#### 2. キャッシュ戦略
- 読み取り専用データの積極キャッシング
- 更新頻度に応じたTTL設定
- キャッシュ無効化の適切なタイミング

#### 3. WebSocket最適化
- 接続プール管理
- メッセージの batch処理
- 不要な接続の自動切断

---

## 🎯 まとめ

### ✅ 習得すべきスキル

1. **API設計理解**: RESTful API の基本原則
2. **データバリデーション**: Pydantic スキーマによる型安全性
3. **リアルタイム通信**: WebSocket を活用した双方向通信  
4. **エラーハンドリング**: 適切なHTTPステータスコードとメッセージ
5. **パフォーマンス**: キャッシング戦略と最適化手法

### 🚀 次のステップ

1. **フロントエンド統合**: React/Vue との OpenAPI-TS 連携
2. **認証システム**: JWT による API セキュリティ
3. **監視・ログ**: Prometheus, Grafana によるメトリクス収集
4. **本格運用**: Docker Compose による本番環境構築

### 📚 参考資料

- **FastAPI 公式ドキュメント**: https://fastapi.tiangolo.com/
- **WebSocket API**: https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API
- **Redis コマンドリファレンス**: https://redis.io/commands
- **PostgreSQL パフォーマンスチューニング**: https://www.postgresql.org/docs/current/performance-tips.html

**🎊 FastAPI 実践マスターお疲れ様でした！本格的なリアルタイム監視システムが完成です。**