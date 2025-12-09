"""
Price management service
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from typing import List, Optional
from datetime import datetime
import structlog

from app.models.price import Price, PriceHistory
from app.schemas.price import PriceCreate, PriceUpdate, PriceChangeAlert
from app.core.redis_client import redis_manager, CACHE_KEYS
from app.core.config import settings

logger = structlog.get_logger(__name__)


class PriceService:
    """Price management service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all_prices(self, skip: int = 0, limit: int = 100) -> List[Price]:
        """Get all current prices with pagination"""
        query = (
            select(Price)
            .where(Price.is_active == True)
            .offset(skip)
            .limit(limit)
            .order_by(Price.effective_from.desc())
        )
        result = await self.db.execute(query)
        prices = result.scalars().all()
        
        logger.info("Retrieved price list from database", count=len(prices))
        return prices
    
    async def get_current_price(self, item_id: int) -> Optional[Price]:
        """Get current active price for item"""
        # Check cache first
        cache_key = CACHE_KEYS["price_current"].format(item_id=item_id)
        cached_result = await redis_manager.get_cache(cache_key)
        
        if cached_result:
            logger.info("Retrieved current price from cache", item_id=item_id)
            return cached_result
        
        # Query database
        query = (
            select(Price)
            .where(
                and_(
                    Price.inventory_id == item_id,
                    Price.is_active == True,
                    Price.effective_from <= datetime.utcnow()
                )
            )
            .order_by(Price.effective_from.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        price = result.scalar_one_or_none()
        
        if price:
            # Cache for 30 minutes
            await redis_manager.set_cache(cache_key, price.__dict__, expiry=1800)
            logger.info("Retrieved current price from database", item_id=item_id, price=price.selling_price)
        
        return price
    
    async def create_or_update_price(self, price_data: PriceCreate) -> Price:
        """Create or update price for an item"""
        # Get existing price to track changes
        existing_price = await self.get_current_price(price_data.inventory_id)
        
        # Deactivate existing price if exists
        if existing_price:
            existing_price.is_active = False
            existing_price.effective_until = datetime.utcnow()
        
        # Create new price record
        db_price = Price(**price_data.model_dump())
        self.db.add(db_price)
        
        if existing_price:
            await self.db.commit()
            await self.db.refresh(db_price)
            
            # Record price change history
            await self._record_price_history(
                inventory_id=price_data.inventory_id,
                old_price=existing_price.selling_price,
                new_price=db_price.selling_price,
                change_reason="manual_update",
                change_type="manual"
            )
            
            # Check for significant price change
            price_change_percent = abs((db_price.selling_price - existing_price.selling_price) / existing_price.selling_price * 100)
            if price_change_percent >= settings.PRICE_CHANGE_THRESHOLD * 100:
                await self._send_price_change_alert(existing_price, db_price, price_change_percent)
        
        await self.db.commit()
        await self.db.refresh(db_price)
        
        # Invalidate cache
        await self._invalidate_price_caches(price_data.inventory_id)
        
        # Send real-time update
        await self._send_price_update(db_price, "created" if not existing_price else "updated")
        
        logger.info("Created/updated price", item_id=price_data.inventory_id, new_price=db_price.selling_price)
        return db_price
    
    async def update_price(self, item_id: int, price_update: PriceUpdate) -> Optional[Price]:
        """Update existing price"""
        # Get current price
        current_price = await self.get_current_price(item_id)
        if not current_price:
            return None
        
        # Get old price for history tracking
        old_price = current_price.selling_price
        
        # Update price
        update_data = price_update.model_dump(exclude_unset=True)
        
        query = (
            update(Price)
            .where(Price.id == current_price.id)
            .values(**update_data)
            .returning(Price)
        )
        result = await self.db.execute(query)
        await self.db.commit()
        updated_price = result.scalar_one_or_none()
        
        if updated_price and "selling_price" in update_data:
            # Record price change history
            await self._record_price_history(
                inventory_id=item_id,
                old_price=old_price,
                new_price=updated_price.selling_price,
                change_reason=price_update.change_reason or "price_update",
                change_type="manual"
            )
            
            # Check for significant change
            price_change_percent = abs((updated_price.selling_price - old_price) / old_price * 100)
            if price_change_percent >= settings.PRICE_CHANGE_THRESHOLD * 100:
                # Create temporary old price object for alert
                old_price_obj = Price(selling_price=old_price, inventory_id=item_id)
                await self._send_price_change_alert(old_price_obj, updated_price, price_change_percent)
        
        # Invalidate cache
        await self._invalidate_price_caches(item_id)
        
        # Send real-time update
        if updated_price:
            await self._send_price_update(updated_price, "updated")
            logger.info("Updated price", item_id=item_id, new_price=updated_price.selling_price)
        
        return updated_price
    
    async def get_price_history(self, item_id: int, start_date: datetime) -> List[PriceHistory]:
        """Get price change history for item"""
        # Check cache first
        cache_key = CACHE_KEYS["price_history"].format(item_id=item_id, days=(datetime.utcnow() - start_date).days)
        cached_result = await redis_manager.get_cache(cache_key)
        
        if cached_result:
            logger.info("Retrieved price history from cache", item_id=item_id)
            return cached_result
        
        # Query database
        query = (
            select(PriceHistory)
            .where(
                and_(
                    PriceHistory.inventory_id == item_id,
                    PriceHistory.changed_at >= start_date
                )
            )
            .order_by(PriceHistory.changed_at.desc())
        )
        result = await self.db.execute(query)
        history = result.scalars().all()
        
        # Cache for 1 hour
        await redis_manager.set_cache(cache_key, [h.__dict__ for h in history], expiry=3600)
        
        logger.info("Retrieved price history from database", item_id=item_id, count=len(history))
        return history
    
    async def get_significant_price_changes(self, threshold_percent: float, start_date: datetime) -> List[PriceHistory]:
        """Get items with significant price changes"""
        query = (
            select(PriceHistory)
            .where(
                and_(
                    PriceHistory.changed_at >= start_date,
                    PriceHistory.price_change_percent >= threshold_percent
                )
            )
            .order_by(PriceHistory.price_change_percent.desc())
        )
        result = await self.db.execute(query)
        changes = result.scalars().all()
        
        logger.info("Retrieved significant price changes", threshold=threshold_percent, count=len(changes))
        return changes
    
    async def _record_price_history(self, inventory_id: int, old_price: float, new_price: float, 
                                   change_reason: str = None, change_type: str = "manual"):
        """Record price change in history"""
        price_change_amount = new_price - old_price
        price_change_percent = (price_change_amount / old_price * 100) if old_price > 0 else 0
        
        history_record = PriceHistory(
            inventory_id=inventory_id,
            old_price=old_price,
            new_price=new_price,
            price_change_percent=price_change_percent,
            price_change_amount=price_change_amount,
            change_reason=change_reason,
            change_type=change_type
        )
        
        self.db.add(history_record)
        # Note: commit will be handled by caller
        
        logger.info("Recorded price history", 
                   inventory_id=inventory_id, 
                   change_percent=round(price_change_percent, 2))
    
    async def _invalidate_price_caches(self, item_id: int):
        """Invalidate relevant price caches"""
        cache_key = CACHE_KEYS["price_current"].format(item_id=item_id)
        await redis_manager.delete_cache(cache_key)
        
        # Clear history caches
        for days in [7, 30, 90]:
            cache_key = CACHE_KEYS["price_history"].format(item_id=item_id, days=days)
            await redis_manager.delete_cache(cache_key)
    
    async def _send_price_update(self, price: Price, action: str):
        """Send real-time price update notification"""
        from app.services.websocket_manager import ConnectionManager
        
        manager = ConnectionManager()
        
        await manager.send_price_update({
            "action": action,
            "price": {
                "id": price.id,
                "inventory_id": price.inventory_id,
                "selling_price": price.selling_price,
                "cost_price": price.cost_price,
                "discount_price": price.discount_price,
                "final_price": price.final_price,
                "margin_percent": price.calculated_margin,
                "effective_from": price.effective_from.isoformat() if price.effective_from else None
            }
        })
    
    async def _send_price_change_alert(self, old_price: Price, new_price: Price, change_percent: float):
        """Send price change alert for significant changes"""
        from app.services.websocket_manager import ConnectionManager
        
        manager = ConnectionManager()
        
        # Determine alert type
        if change_percent >= 20:
            alert_type = "major_change"
        elif new_price.selling_price > old_price.selling_price:
            alert_type = "significant_increase"
        else:
            alert_type = "significant_decrease"
        
        alert_data = PriceChangeAlert(
            inventory_id=new_price.inventory_id,
            sku=f"ITEM-{new_price.inventory_id}",  # Would get from inventory in real implementation
            item_name="Item Name",  # Would get from inventory in real implementation
            old_price=old_price.selling_price,
            new_price=new_price.selling_price,
            change_percent=change_percent,
            change_amount=new_price.selling_price - old_price.selling_price,
            alert_type=alert_type,
            timestamp=datetime.utcnow()
        )
        
        await manager.send_price_alert(alert_data.model_dump())