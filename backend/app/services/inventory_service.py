"""
Inventory business logic service
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
import structlog

from app.models.inventory import Inventory
from app.schemas.inventory import InventoryCreate, InventoryUpdate, InventoryStockAlert
from app.core.redis_client import redis_manager, CACHE_KEYS
from app.core.config import settings

logger = structlog.get_logger(__name__)


class InventoryService:
    """Inventory management service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all_inventory(self, skip: int = 0, limit: int = 100) -> List[Inventory]:
        """Get all inventory items with pagination"""
        # Check cache first
        cache_key = CACHE_KEYS["inventory_list"].format(skip=skip, limit=limit)
        cached_result = await redis_manager.get_cache(cache_key)
        
        if cached_result:
            logger.info("Retrieved inventory list from cache")
            # Convert dict back to Inventory objects (simplified for now)
            return cached_result
        
        # Query database
        query = select(Inventory).offset(skip).limit(limit).order_by(Inventory.created_at.desc())
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        # Cache result for 5 minutes
        await redis_manager.set_cache(cache_key, [item.__dict__ for item in items], expiry=300)
        
        logger.info("Retrieved inventory list from database", count=len(items))
        return items
    
    async def get_inventory_by_id(self, item_id: int) -> Optional[Inventory]:
        """Get inventory item by ID"""
        # Check cache first
        cache_key = CACHE_KEYS["inventory_item"].format(item_id=item_id)
        cached_result = await redis_manager.get_cache(cache_key)
        
        if cached_result:
            logger.info("Retrieved inventory item from cache", item_id=item_id)
            return cached_result
        
        # Query database
        query = select(Inventory).where(Inventory.id == item_id)
        result = await self.db.execute(query)
        item = result.scalar_one_or_none()
        
        if item:
            # Cache for 10 minutes
            await redis_manager.set_cache(cache_key, item.__dict__, expiry=600)
            logger.info("Retrieved inventory item from database", item_id=item_id)
        
        return item
    
    async def create_inventory(self, inventory_data: InventoryCreate) -> Inventory:
        """Create new inventory item"""
        # Calculate available quantity
        available_quantity = inventory_data.stock_quantity - inventory_data.reserved_quantity
        
        # Create new inventory item
        db_inventory = Inventory(
            **inventory_data.model_dump(),
            available_quantity=available_quantity
        )
        
        self.db.add(db_inventory)
        await self.db.commit()
        await self.db.refresh(db_inventory)
        
        # Invalidate cache
        await self._invalidate_inventory_caches()
        
        # Send real-time update
        await self._send_inventory_update(db_inventory, "created")
        
        logger.info("Created new inventory item", item_id=db_inventory.id, sku=db_inventory.sku)
        return db_inventory
    
    async def update_inventory(self, item_id: int, inventory_update: InventoryUpdate) -> Optional[Inventory]:
        """Update inventory item"""
        # Get existing item
        existing_item = await self.get_inventory_by_id(item_id)
        if not existing_item:
            return None
        
        # Prepare update data
        update_data = inventory_update.model_dump(exclude_unset=True)
        
        # Recalculate available quantity if stock or reserved changed
        if "stock_quantity" in update_data or "reserved_quantity" in update_data:
            new_stock = update_data.get("stock_quantity", existing_item.stock_quantity)
            new_reserved = update_data.get("reserved_quantity", existing_item.reserved_quantity)
            update_data["available_quantity"] = new_stock - new_reserved
        
        # Update database
        query = (
            update(Inventory)
            .where(Inventory.id == item_id)
            .values(**update_data)
            .returning(Inventory)
        )
        result = await self.db.execute(query)
        await self.db.commit()
        updated_item = result.scalar_one_or_none()
        
        if updated_item:
            # Invalidate cache
            await self._invalidate_inventory_caches(item_id)
            
            # Check for low stock alert
            if updated_item.is_low_stock:
                await self._send_stock_alert(updated_item)
            
            # Send real-time update
            await self._send_inventory_update(updated_item, "updated")
            
            logger.info("Updated inventory item", item_id=item_id, sku=updated_item.sku)
        
        return updated_item
    
    async def delete_inventory(self, item_id: int) -> bool:
        """Delete inventory item"""
        # Check if item exists
        existing_item = await self.get_inventory_by_id(item_id)
        if not existing_item:
            return False
        
        # Delete from database
        query = delete(Inventory).where(Inventory.id == item_id)
        await self.db.execute(query)
        await self.db.commit()
        
        # Invalidate cache
        await self._invalidate_inventory_caches(item_id)
        
        # Send real-time update
        await self._send_inventory_update(existing_item, "deleted")
        
        logger.info("Deleted inventory item", item_id=item_id, sku=existing_item.sku)
        return True
    
    async def get_low_stock_items(self, threshold: Optional[int] = None) -> List[InventoryStockAlert]:
        """Get items with low stock levels"""
        if threshold is None:
            threshold = settings.LOW_STOCK_THRESHOLD
        
        # Check cache first
        cache_key = CACHE_KEYS["low_stock_items"].format(threshold=threshold)
        cached_result = await redis_manager.get_cache(cache_key)
        
        if cached_result:
            logger.info("Retrieved low stock items from cache")
            return cached_result
        
        # Query database
        query = (
            select(Inventory)
            .where(Inventory.available_quantity <= threshold)
            .where(Inventory.is_active == True)
            .order_by(Inventory.available_quantity.asc())
        )
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        # Convert to alert format
        alerts = []
        for item in items:
            alert_level = "out_of_stock" if item.available_quantity <= 0 else "low" if item.available_quantity <= item.min_stock_level else "critical"
            
            alerts.append(InventoryStockAlert(
                id=item.id,
                sku=item.sku,
                name=item.name,
                current_stock=item.available_quantity,
                min_stock_level=item.min_stock_level,
                shortage_amount=max(0, item.min_stock_level - item.available_quantity),
                alert_level=alert_level
            ))
        
        # Cache for 2 minutes (frequent updates needed for stock levels)
        await redis_manager.set_cache(cache_key, [alert.model_dump() for alert in alerts], expiry=120)
        
        logger.info("Retrieved low stock items from database", count=len(alerts))
        return alerts
    
    async def get_low_stock_inventory_items(self, threshold: Optional[int] = None) -> List[Inventory]:
        """Get inventory items with low stock levels (returns full inventory objects)"""
        if threshold is None:
            threshold = settings.LOW_STOCK_THRESHOLD
        
        # Query database for items that are out of stock or below minimum level
        query = (
            select(Inventory)
            .where(
                (Inventory.stock_quantity <= 0) |  # Out of stock
                (Inventory.stock_quantity <= Inventory.min_stock_level)  # Below minimum level
            )
            .where(Inventory.is_active == True)
            .order_by(Inventory.stock_quantity.asc())
        )
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        logger.info("Retrieved low stock inventory items", count=len(items))
        return items
    
    async def get_inventory_stats(self) -> dict:
        """Get comprehensive inventory statistics"""
        # 全アイテムを取得
        query = select(Inventory).where(Inventory.is_active == True)
        result = await self.db.execute(query)
        all_items = result.scalars().all()
        
        # 統計を計算
        total_items = len(all_items)
        out_of_stock_count = len([item for item in all_items if item.stock_quantity <= 0])
        low_stock_count = len([item for item in all_items if 0 < item.stock_quantity <= item.min_stock_level])
        
        # 総在庫価値を計算
        total_value = sum(item.stock_quantity * item.cost_price for item in all_items)
        
        # 在庫状況の割合
        normal_stock_count = total_items - out_of_stock_count - low_stock_count
        normal_stock_percentage = (normal_stock_count / total_items * 100) if total_items > 0 else 0
        low_stock_percentage = (low_stock_count / total_items * 100) if total_items > 0 else 0
        out_of_stock_percentage = (out_of_stock_count / total_items * 100) if total_items > 0 else 0
        
        stats = {
            "total_items": total_items,
            "out_of_stock_count": out_of_stock_count,
            "low_stock_count": low_stock_count,
            "normal_stock_count": normal_stock_count,
            "total_value": total_value,
            "normal_stock_percentage": round(normal_stock_percentage, 1),
            "low_stock_percentage": round(low_stock_percentage, 1),
            "out_of_stock_percentage": round(out_of_stock_percentage, 1),
        }
        
        logger.info("Retrieved inventory statistics", stats=stats)
        return stats
    
    async def _invalidate_inventory_caches(self, item_id: Optional[int] = None):
        """Invalidate relevant caches"""
        if item_id:
            cache_key = CACHE_KEYS["inventory_item"].format(item_id=item_id)
            await redis_manager.delete_cache(cache_key)
        
        # Clear list caches (simplified - in production, use pattern matching)
        for skip in range(0, 1000, 100):  # Clear first 10 pages
            cache_key = CACHE_KEYS["inventory_list"].format(skip=skip, limit=100)
            await redis_manager.delete_cache(cache_key)
        
        # Clear alert caches
        for threshold in [5, 10, 20, 50]:
            cache_key = CACHE_KEYS["low_stock_items"].format(threshold=threshold)
            await redis_manager.delete_cache(cache_key)
    
    async def _send_inventory_update(self, inventory: Inventory, action: str):
        """Send real-time inventory update notification"""
        from app.services.websocket_manager import ConnectionManager
        
        # Create manager instance (in production, use dependency injection)
        manager = ConnectionManager()
        
        await manager.send_inventory_update({
            "action": action,
            "item": {
                "id": inventory.id,
                "sku": inventory.sku,
                "name": inventory.name,
                "stock_quantity": inventory.stock_quantity,
                "available_quantity": inventory.available_quantity,
                "is_low_stock": inventory.is_low_stock,
                "stock_status": inventory.stock_status
            }
        })
    
    async def _send_stock_alert(self, inventory: Inventory):
        """Send stock level alert"""
        from app.services.websocket_manager import ConnectionManager
        
        manager = ConnectionManager()
        
        alert_level = "critical" if inventory.available_quantity <= 0 else "warning"
        
        await manager.send_stock_alert({
            "item_id": inventory.id,
            "sku": inventory.sku,
            "name": inventory.name,
            "current_stock": inventory.available_quantity,
            "min_stock_level": inventory.min_stock_level,
            "alert_level": alert_level,
            "message": f"Stock level for {inventory.sku} is {'out of stock' if inventory.available_quantity <= 0 else 'below minimum threshold'}"
        })