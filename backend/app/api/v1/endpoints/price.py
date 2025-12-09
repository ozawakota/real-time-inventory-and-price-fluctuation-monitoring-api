"""
Price management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime, timedelta

from app.db.session import get_db
from app.schemas.price import PriceCreate, PriceUpdate, PriceResponse, PriceHistoryResponse
from app.services.price_service import PriceService

router = APIRouter()


@router.get("/", response_model=List[PriceResponse])
async def get_all_prices(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all current prices"""
    service = PriceService(db)
    return await service.get_all_prices(skip=skip, limit=limit)


@router.get("/{item_id}", response_model=PriceResponse)
async def get_item_price(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get current price for specific item"""
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
    """Create or update price for an item"""
    service = PriceService(db)
    return await service.create_or_update_price(price)


@router.put("/{item_id}", response_model=PriceResponse)
async def update_price(
    item_id: int,
    price_update: PriceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update price for specific item"""
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
    """Get price change history for specific item"""
    service = PriceService(db)
    start_date = datetime.utcnow() - timedelta(days=days)
    return await service.get_price_history(item_id, start_date)


@router.get("/changes/significant")
async def get_significant_price_changes(
    threshold_percent: float = 5.0,
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """Get items with significant price changes"""
    service = PriceService(db)
    start_date = datetime.utcnow() - timedelta(hours=hours)
    return await service.get_significant_price_changes(threshold_percent, start_date)