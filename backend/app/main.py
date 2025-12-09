"""
リアルタイム在庫・価格変動監視ダッシュボードAPI
Real-Time Inventory & Price Monitoring API System
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings
from app.core.database import init_db
from app.core.redis_client import init_redis
from app.api.v1.api import api_router
from app.services.websocket_manager import ConnectionManager

# Configure structured logging
logger = structlog.get_logger(__name__)

# WebSocket connection manager
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    # Startup
    logger.info("Starting Real-Time Inventory Monitoring API")
    await init_redis()
    await init_db()
    logger.info("Database and Redis connections established")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Real-Time Inventory Monitoring API")


# FastAPI application instance
app = FastAPI(
    title="Real-Time Inventory & Price Monitoring API",
    description="ECサイト向けリアルタイム在庫・価格変動監視システム",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Real-Time Inventory & Price Monitoring API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "inventory-monitoring-api"}


@app.websocket("/ws/inventory")
async def websocket_inventory_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time inventory updates"""
    await manager.connect(websocket)
    logger.info("WebSocket client connected")
    
    try:
        while True:
            # Keep connection alive and listen for any client messages
            data = await websocket.receive_text()
            logger.info("Received WebSocket message", data=data)
            
            # Echo back for connection test
            await websocket.send_text(f"Message received: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")


@app.websocket("/ws/price")
async def websocket_price_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time price updates"""
    await manager.connect(websocket)
    logger.info("Price monitoring WebSocket client connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.info("Received price monitoring message", data=data)
            await websocket.send_text(f"Price update received: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Price monitoring WebSocket client disconnected")