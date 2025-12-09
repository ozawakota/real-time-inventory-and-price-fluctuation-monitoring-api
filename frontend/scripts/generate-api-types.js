#!/usr/bin/env node

/**
 * OpenAPI TypeScript型定義生成スクリプト
 * FastAPIのOpenAPIスキーマからTypeScript型定義とAPIクライアントを自動生成
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// 設定
const CONFIG = {
  // FastAPI OpenAPI URL (開発環境)
  OPENAPI_URL: 'http://localhost:8000/openapi.json',
  
  // ローカルOpenAPIファイル (バックアップ用)
  LOCAL_OPENAPI_PATH: '../backend/openapi.json',
  
  // 出力ディレクトリ
  OUTPUT_DIR: './src/lib/api',
  
  // 生成オプション
  CLIENT_TYPE: 'axios', // axios, fetch, node
};

/**
 * OpenAPIスキーマをローカルに保存
 */
async function saveOpenAPISchema() {
  try {
    console.log('📡 Fetching OpenAPI schema from FastAPI...');
    
    // FastAPIが起動しているかチェック
    execSync(`curl -f ${CONFIG.OPENAPI_URL} -o openapi.json`, { 
      stdio: 'pipe',
      timeout: 5000 
    });
    
    console.log('✅ OpenAPI schema saved successfully');
    return 'openapi.json';
    
  } catch (error) {
    console.warn('⚠️  FastAPI server not available, checking for local schema...');
    
    // ローカルファイルが存在するかチェック
    if (fs.existsSync(CONFIG.LOCAL_OPENAPI_PATH)) {
      console.log('📁 Using local OpenAPI schema');
      return CONFIG.LOCAL_OPENAPI_PATH;
    }
    
    throw new Error('OpenAPI schema not available. Please start the FastAPI server or provide a local schema file.');
  }
}

/**
 * TypeScript型定義とAPIクライアントを生成
 */
async function generateTypes(schemaPath) {
  try {
    console.log('🔧 Generating TypeScript types and API client...');
    
    // 出力ディレクトリの作成
    if (!fs.existsSync(CONFIG.OUTPUT_DIR)) {
      fs.mkdirSync(CONFIG.OUTPUT_DIR, { recursive: true });
    }
    
    // openapi-typescript コマンドの実行
    const command = `npx openapi-typescript ${schemaPath} --output ${CONFIG.OUTPUT_DIR}/schema.ts`;
    execSync(command, { stdio: 'inherit' });
    
    console.log('✅ TypeScript types generated successfully');
    
    // APIクライアント生成用のテンプレートを作成
    await generateApiClient();
    
  } catch (error) {
    console.error('❌ Failed to generate types:', error.message);
    throw error;
  }
}

/**
 * APIクライアントテンプレートを生成
 */
async function generateApiClient() {
  const clientTemplate = `/**
 * Generated API Client
 * 
 * This file contains type-safe API client functions for the Real-Time Inventory API.
 * Generated from OpenAPI schema using openapi-typescript.
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import type { paths, components } from './schema';

// Type definitions from OpenAPI schema
export type InventoryItem = components['schemas']['InventoryResponse'];
export type InventoryCreate = components['schemas']['InventoryCreate'];
export type InventoryUpdate = components['schemas']['InventoryUpdate'];
export type PriceItem = components['schemas']['PriceResponse'];
export type PriceCreate = components['schemas']['PriceCreate'];
export type PriceUpdate = components['schemas']['PriceUpdate'];
export type PriceHistory = components['schemas']['PriceHistoryResponse'];

// API Response types
type ApiResponse<T> = AxiosResponse<T>;

export class InventoryAPIClient {
  private client: AxiosInstance;

  constructor(baseURL: string = 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Inventory endpoints
  async getInventory(skip = 0, limit = 100): Promise<ApiResponse<InventoryItem[]>> {
    return this.client.get(\`/api/v1/inventory/?skip=\${skip}&limit=\${limit}\`);
  }

  async getInventoryItem(itemId: number): Promise<ApiResponse<InventoryItem>> {
    return this.client.get(\`/api/v1/inventory/\${itemId}\`);
  }

  async createInventoryItem(data: InventoryCreate): Promise<ApiResponse<InventoryItem>> {
    return this.client.post('/api/v1/inventory/', data);
  }

  async updateInventoryItem(itemId: number, data: InventoryUpdate): Promise<ApiResponse<InventoryItem>> {
    return this.client.put(\`/api/v1/inventory/\${itemId}\`, data);
  }

  async deleteInventoryItem(itemId: number): Promise<ApiResponse<{ message: string }>> {
    return this.client.delete(\`/api/v1/inventory/\${itemId}\`);
  }

  async getLowStockItems(threshold = 10): Promise<ApiResponse<InventoryItem[]>> {
    return this.client.get(\`/api/v1/inventory/low-stock/alert?threshold=\${threshold}\`);
  }

  // Price endpoints
  async getPrices(skip = 0, limit = 100): Promise<ApiResponse<PriceItem[]>> {
    return this.client.get(\`/api/v1/price/?skip=\${skip}&limit=\${limit}\`);
  }

  async getItemPrice(itemId: number): Promise<ApiResponse<PriceItem>> {
    return this.client.get(\`/api/v1/price/\${itemId}\`);
  }

  async createPrice(data: PriceCreate): Promise<ApiResponse<PriceItem>> {
    return this.client.post('/api/v1/price/', data);
  }

  async updatePrice(itemId: number, data: PriceUpdate): Promise<ApiResponse<PriceItem>> {
    return this.client.put(\`/api/v1/price/\${itemId}\`, data);
  }

  async getPriceHistory(itemId: number, days = 30): Promise<ApiResponse<PriceHistory[]>> {
    return this.client.get(\`/api/v1/price/\${itemId}/history?days=\${days}\`);
  }

  async getSignificantPriceChanges(thresholdPercent = 5.0, hours = 24): Promise<ApiResponse<PriceHistory[]>> {
    return this.client.get(\`/api/v1/price/changes/significant?threshold_percent=\${thresholdPercent}&hours=\${hours}\`);
  }
}

// Default API client instance
export const apiClient = new InventoryAPIClient();

// WebSocket connection helper
export class InventoryWebSocketClient {
  private ws: WebSocket | null = null;
  private baseURL: string;

  constructor(baseURL: string = 'ws://localhost:8000') {
    this.baseURL = baseURL;
  }

  connectToInventory(onMessage: (data: any) => void, onError?: (error: Event) => void): void {
    this.ws = new WebSocket(\`\${this.baseURL}/ws/inventory\`);
    
    this.ws.onopen = () => {
      console.log('📡 WebSocket connected to inventory updates');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('📡 WebSocket disconnected from inventory updates');
    };

    this.ws.onerror = (error) => {
      console.error('📡 WebSocket error:', error);
      if (onError) onError(error);
    };
  }

  connectToPrice(onMessage: (data: any) => void, onError?: (error: Event) => void): void {
    this.ws = new WebSocket(\`\${this.baseURL}/ws/price\`);
    
    this.ws.onopen = () => {
      console.log('📡 WebSocket connected to price updates');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('📡 WebSocket disconnected from price updates');
    };

    this.ws.onerror = (error) => {
      console.error('📡 WebSocket error:', error);
      if (onError) onError(error);
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Default WebSocket client instance
export const wsClient = new InventoryWebSocketClient();
`;

  const clientPath = path.join(CONFIG.OUTPUT_DIR, 'client.ts');
  fs.writeFileSync(clientPath, clientTemplate);
  
  console.log('✅ API client generated successfully');
}

/**
 * クリーンアップ関数
 */
function cleanup() {
  // 一時的なOpenAPIファイルを削除
  if (fs.existsSync('openapi.json')) {
    fs.unlinkSync('openapi.json');
  }
}

/**
 * メイン実行関数
 */
async function main() {
  try {
    console.log('🚀 Starting OpenAPI TypeScript generation...');
    
    // OpenAPIスキーマの取得
    const schemaPath = await saveOpenAPISchema();
    
    // TypeScript型定義の生成
    await generateTypes(schemaPath);
    
    console.log('');
    console.log('🎉 TypeScript types generation completed successfully!');
    console.log('');
    console.log('📁 Generated files:');
    console.log(\`   - \${CONFIG.OUTPUT_DIR}/schema.ts (OpenAPI types)\`);
    console.log(\`   - \${CONFIG.OUTPUT_DIR}/client.ts (API client)\`);
    console.log('');
    console.log('💡 Usage:');
    console.log('   import { apiClient, wsClient, type InventoryItem } from "./src/lib/api/client";');
    
  } catch (error) {
    console.error('');
    console.error('❌ Generation failed:');
    console.error('  ', error.message);
    console.error('');
    console.error('💡 Make sure:');
    console.error('   1. FastAPI server is running (http://localhost:8000)');
    console.error('   2. openapi-typescript is installed (npm install)');
    console.error('   3. Output directory is writable');
    
    process.exit(1);
  } finally {
    cleanup();
  }
}

// スクリプトが直接実行された場合のみmain関数を実行
if (require.main === module) {
  main();
}

module.exports = { main, generateTypes, saveOpenAPISchema };