# Project Structure

## Organization Philosophy

**Domain-Driven Monorepo**: backend/frontend 分離による責務明確化、OpenAPI-TS自動連携による統合開発

**Layer-Based Backend**: FastAPI標準のapp内レイヤー構造 (api/core/models/schemas/services)

**Feature-Centric Frontend**: React hooks パターンによる機能別モジュール化

## Directory Patterns

### Backend API Layer
**Location**: `backend/app/api/v1/endpoints/`  
**Purpose**: REST API エンドポイント定義、ビジネスロジックはservicesに委譲  
**Example**: `inventory.py`, `price.py` - ドメイン別エンドポイント分割

### Backend Business Logic
**Location**: `backend/app/services/`  
**Purpose**: ビジネスロジック、データベース操作、キャッシング制御  
**Example**: `inventory_service.py` - CRUD + Redis + WebSocket統合

### Backend Models & Schemas
**Location**: `backend/app/models/` + `backend/app/schemas/`  
**Purpose**: SQLAlchemy ORM (models) と Pydantic validation (schemas) の分離  
**Example**: `models/inventory.py` (DB), `schemas/inventory.py` (API)

### Frontend API Integration
**Location**: `frontend/src/lib/api/`  
**Purpose**: OpenAPI-TS 自動生成型定義とAPIクライアント  
**Example**: `schema.ts` (自動生成), `client.ts` (型安全クライアント)

### Frontend React Hooks
**Location**: `frontend/src/lib/hooks/`  
**Purpose**: React Query hooks、ドメイン別に分離、リアルタイム統合  
**Example**: `use-inventory.ts`, `use-price.ts`, `use-websocket.ts`

## Naming Conventions

**Backend Files**: `snake_case.py` (Python標準)  
**Frontend Files**: `kebab-case.ts` (Next.js規約)  
**API Endpoints**: REST標準 (`GET /api/v1/inventory/`)  
**WebSocket Endpoints**: ドメイン別 (`/ws/inventory`, `/ws/price`)

**Database Models**: `PascalCase` classes (`Inventory`, `Price`)  
**Pydantic Schemas**: `PascalCase` + suffix (`InventoryCreate`, `InventoryResponse`)  
**React Hooks**: `use` + `PascalCase` (`useInventoryList`, `usePriceHistory`)

## Import Organization

### Backend Patterns
```python
# Absolute from app root
from app.core.config import settings
from app.models.inventory import Inventory
from app.services.inventory_service import InventoryService

# Relative for local
from .schemas import InventoryCreate
```

### Frontend Patterns  
```typescript
// Auto-generated types (absolute)
import { apiClient, type InventoryItem } from '../lib/api/client'

// Hooks (relative)
import { useInventoryList } from '../lib/hooks/use-inventory'

// Local components
import { InventoryCard } from './InventoryCard'
```

**Path Aliases**:
- Backend: `app.` prefix for absolute imports
- Frontend: `../lib/` for shared utilities

## Code Organization Principles

**Service Layer Isolation**: API endpoints → Services → Models の単方向依存

**Type-First Development**: Pydantic schemas → OpenAPI → TypeScript types の自動連携

**WebSocket Centralization**: `websocket_manager.py` による接続とメッセージング統合管理

**React Query Caching**: hooks layer でのキャッシング戦略集約、楽観的更新パターン

**Real-time Integration**: backend services → Redis Pub/Sub → WebSocket → React hooks の一貫フロー

---
_Clear boundaries enable automatic type safety and real-time synchronization_