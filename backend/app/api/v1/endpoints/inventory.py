"""
Inventory management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.inventory import InventoryCreate, InventoryUpdate, InventoryResponse
from app.services.inventory_service import InventoryService

router = APIRouter()


@router.get("/", response_model=List[InventoryResponse])
async def get_all_inventory(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all inventory items"""
    service = InventoryService(db)
    return await service.get_all_inventory(skip=skip, limit=limit)


@router.get("/{item_id}", response_model=InventoryResponse)
async def get_inventory_item(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get specific inventory item"""
    service = InventoryService(db)
    item = await service.get_inventory_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.post("/", response_model=InventoryResponse)
async def create_inventory_item(
    item: InventoryCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new inventory item"""
    service = InventoryService(db)
    return await service.create_inventory(item)


@router.put("/{item_id}", response_model=InventoryResponse)
async def update_inventory_item(
    item_id: int,
    item_update: InventoryUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update inventory item"""
    service = InventoryService(db)
    updated_item = await service.update_inventory(item_id, item_update)
    if not updated_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return updated_item


@router.delete("/{item_id}")
async def delete_inventory_item(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete inventory item"""
    service = InventoryService(db)
    success = await service.delete_inventory(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return {"message": "Inventory item deleted successfully"}


@router.get("/low-stock/alert")
async def get_low_stock_items(
    threshold: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get items with low stock levels"""
    service = InventoryService(db)
    return await service.get_low_stock_items(threshold)