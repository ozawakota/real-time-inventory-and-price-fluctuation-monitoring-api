"""
Redis client configuration and management
"""
import redis.asyncio as redis
import structlog
import json
from typing import Any, Dict, Optional

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Global Redis connection pool
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            retry_on_timeout=True,
            socket_keepalive=True,
            health_check_interval=30
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established successfully")
        
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        raise


async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    global redis_client
    if redis_client is None:
        await init_redis()
    return redis_client


class RedisManager:
    """Redis operations manager"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
    
    async def get_client(self) -> redis.Redis:
        """Get Redis client"""
        if self.client is None:
            self.client = await get_redis()
        return self.client
    
    async def set_cache(self, key: str, value: Any, expiry: int = 3600):
        """Set cache with expiry"""
        client = await self.get_client()
        serialized_value = json.dumps(value, default=str)
        await client.setex(key, expiry, serialized_value)
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value"""
        client = await self.get_client()
        cached_value = await client.get(key)
        if cached_value:
            try:
                return json.loads(cached_value)
            except json.JSONDecodeError:
                logger.warning("Failed to decode cached value", key=key)
                return None
        return None
    
    async def delete_cache(self, key: str):
        """Delete cache key"""
        client = await self.get_client()
        await client.delete(key)
    
    async def publish_message(self, channel: str, message: Dict[str, Any]):
        """Publish message to Redis channel"""
        client = await self.get_client()
        serialized_message = json.dumps(message, default=str)
        await client.publish(channel, serialized_message)
        logger.info("Published message to Redis channel", channel=channel, message_type=message.get("type"))
    
    async def subscribe_to_channel(self, channel: str):
        """Subscribe to Redis channel"""
        client = await self.get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        logger.info("Subscribed to Redis channel", channel=channel)
        return pubsub


# Global Redis manager instance
redis_manager = RedisManager()


# Redis channel constants
CHANNELS = {
    "inventory_updates": "inventory:updates",
    "price_updates": "price:updates",
    "stock_alerts": "stock:alerts",
    "price_alerts": "price:alerts",
    "system_notifications": "system:notifications"
}


# Cache key patterns
CACHE_KEYS = {
    "inventory_item": "inventory:item:{item_id}",
    "inventory_list": "inventory:list:{skip}:{limit}",
    "price_current": "price:current:{item_id}",
    "price_history": "price:history:{item_id}:{days}",
    "low_stock_items": "alerts:low_stock:{threshold}",
    "price_changes": "alerts:price_changes:{threshold}:{hours}"
}