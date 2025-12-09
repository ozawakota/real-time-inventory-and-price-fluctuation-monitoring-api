# Technology Stack

## Architecture

**Non-blocking Async Architecture**: 非同期I/O による高並行処理性能重視の設計  
**Event-Driven Real-time**: WebSocket + Redis Pub/Sub によるリアルタイム通信  
**Type-Safe Integration**: OpenAPI-TypeScript による完全型安全なフルスタック統合

## Core Technologies

**Backend**
- **Language**: Python 3.11+
- **Framework**: FastAPI (async/await native)
- **Database**: PostgreSQL 15 (asyncpg driver)
- **Cache/Messaging**: Redis 7 (aioredis client)
- **Real-time**: WebSocket + Redis Pub/Sub

**Frontend**
- **Language**: TypeScript 5.0+
- **Framework**: Next.js 14 (React 18)
- **HTTP Client**: Axios with auto-generated types
- **State Management**: React Query v5 (caching + optimistic updates)
- **Styling**: Tailwind CSS

**Infrastructure**
- **Containerization**: Docker + Docker Compose
- **Development**: uvicorn (reload), nodemon (watch)

## Key Libraries

**Backend Core**
- `fastapi` + `uvicorn`: Async web framework
- `sqlalchemy 2.0` + `asyncpg`: Async ORM and database
- `aioredis` + `redis`: Async Redis client
- `pydantic 2.5`: Data validation and serialization
- `structlog`: Structured logging

**Frontend Core**
- `@tanstack/react-query`: Data fetching + caching
- `react-hook-form` + `zod`: Form handling + validation
- `openapi-typescript`: Auto type generation
- `recharts`: Data visualization
- `react-hot-toast`: Notifications

## Development Standards

### Type Safety
- **Backend**: Pydantic models for 100% data validation
- **Frontend**: TypeScript strict mode, auto-generated API types
- **Integration**: OpenAPI-TS で backend → frontend 完全型同期

### Code Quality
- **Backend**: Python type hints, structlog structured logging
- **Frontend**: ESLint + Prettier, TypeScript strict
- **API**: FastAPI auto-documentation (OpenAPI 3.0)

### Testing
- **Backend**: pytest + pytest-asyncio (async test support)
- **Frontend**: Type checking with tsc --noEmit
- **Integration**: curl examples in documentation

## Development Environment

### Required Tools
- Python 3.11+ & pip
- Node.js 18+ & npm 9+
- Docker & Docker Compose
- Git

### Common Commands
```bash
# Backend Dev
cd backend && uvicorn app.main:app --reload

# Frontend Dev  
cd frontend && npm run dev

# Type Generation
npm run generate-api

# Infrastructure
docker-compose up -d postgres redis
```

## Key Technical Decisions

**Async-First Design**: I/O非同期化による高並行処理 (asyncpg, aioredis, FastAPI async endpoints) ✅
- 実装完了: SQLAlchemy 2.0 + asyncpg ドライバー
- 非同期エンドポイント全面採用
- パフォーマンス検証済み (850+ req/sec)

**Real-time Centralized**: WebSocket接続管理の集約とRedis Pub/Sub 疎結合メッセージング ✅
- WebSocketManager による接続プール管理実装
- Redis チャンネル設計完了 (inventory:updates, price:updates, stock:alerts)
- 自動再接続・エラーハンドリング機構

**Type-Safety Automation**: 手動型定義撲滅、OpenAPI-TS 自動同期 🔄
- OpenAPI-TS 生成スクリプト実装済み
- フロントエンド hooks 基盤完成
- 型安全 API クライアント生成機構確立

**Optimistic Caching**: React Query楽観的更新 + Redis サーバーサイド二段構造 🔄
- Redis キャッシング基盤実装済み
- React Query hooks 設計完了
- キャッシュ無効化戦略確立

**Monorepo Structure**: backend/frontend 統合管理による自動連携 ✅
- 統一プロジェクト構造確立
- 開発環境統合 (Docker Compose)
- ドキュメント統合管理

## 🏗️ Architecture Achievements

**レイヤー分離設計**: API/Service/Model/Schema 完全分離実装
**依存性注入**: FastAPI Depends システム活用
**エラーハンドリング**: 階層化例外処理機構
**包括的ログ**: structlog 構造化ログ実装
**開発者体験**: 詳細ドキュメント + 実践ガイド完備

---
_Performance through async + Type-safety through automation_