"""
WebSocket connection management
"""
from fastapi import WebSocket
from typing import List, Dict, Any
import json
import structlog
import asyncio
from datetime import datetime

from app.core.redis_client import redis_manager, CHANNELS

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        # Store active connections by type
        self.active_connections: Dict[str, List[WebSocket]] = {
            "inventory": [],
            "price": [],
            "alerts": []
        }
        self.subscriber_task: asyncio.Task = None
        self.is_listening = False
    
    async def connect(self, websocket: WebSocket, connection_type: str = "general"):
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        # Determine connection type from WebSocket path
        if "inventory" in str(websocket.url):
            connection_type = "inventory"
        elif "price" in str(websocket.url):
            connection_type = "price"
        elif "alert" in str(websocket.url):
            connection_type = "alerts"
        
        # Add to appropriate connection list
        if connection_type not in self.active_connections:
            self.active_connections[connection_type] = []
        
        self.active_connections[connection_type].append(websocket)
        
        # Start Redis subscriber if not already running
        if not self.is_listening:
            self.subscriber_task = asyncio.create_task(self._start_redis_subscriber())
            self.is_listening = True
        
        logger.info("WebSocket client connected", 
                   connection_type=connection_type,
                   total_connections=sum(len(conns) for conns in self.active_connections.values()))
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        for connection_type, connections in self.active_connections.items():
            if websocket in connections:
                connections.remove(websocket)
                logger.info("WebSocket client disconnected",
                           connection_type=connection_type,
                           remaining_connections=len(connections))
                break
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error("Failed to send personal message", error=str(e))
            self.disconnect(websocket)
    
    async def broadcast_to_type(self, message: Dict[str, Any], connection_type: str):
        """Broadcast message to all connections of specific type"""
        if connection_type not in self.active_connections:
            return
        
        connections = self.active_connections[connection_type].copy()
        message_str = json.dumps(message, default=str)
        
        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning("Failed to send message to WebSocket client", error=str(e))
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
        
        logger.info("Broadcasted message to WebSocket clients",
                   connection_type=connection_type,
                   successful_sends=len(connections) - len(disconnected),
                   failed_sends=len(disconnected))
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all active connections"""
        for connection_type in self.active_connections:
            await self.broadcast_to_type(message, connection_type)
    
    async def _start_redis_subscriber(self):
        """Start Redis subscriber to listen for updates"""
        try:
            # Subscribe to all relevant channels
            channels_to_subscribe = [
                CHANNELS["inventory_updates"],
                CHANNELS["price_updates"],
                CHANNELS["stock_alerts"],
                CHANNELS["price_alerts"],
                CHANNELS["system_notifications"]
            ]
            
            # Create subscriber for each channel
            subscribers = []
            for channel in channels_to_subscribe:
                pubsub = await redis_manager.subscribe_to_channel(channel)
                subscribers.append((channel, pubsub))
            
            logger.info("Started Redis subscribers for WebSocket broadcasting",
                       channels=channels_to_subscribe)
            
            # Listen for messages
            while self.is_listening:
                for channel, pubsub in subscribers:
                    try:
                        message = await asyncio.wait_for(
                            pubsub.get_message(ignore_subscribe_messages=True),
                            timeout=1.0
                        )
                        
                        if message and message.get("data"):
                            await self._handle_redis_message(channel, message["data"])
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error("Error processing Redis message", 
                                   channel=channel, error=str(e))
            
        except Exception as e:
            logger.error("Redis subscriber error", error=str(e))
        finally:
            # Cleanup subscribers
            for _, pubsub in subscribers:
                await pubsub.close()
    
    async def _handle_redis_message(self, channel: str, message_data: str):
        """Handle incoming Redis messages and broadcast to WebSocket clients"""
        try:
            message = json.loads(message_data)
            message["timestamp"] = datetime.utcnow().isoformat()
            message["channel"] = channel
            
            # Route message to appropriate WebSocket connections
            if channel == CHANNELS["inventory_updates"]:
                await self.broadcast_to_type(message, "inventory")
            elif channel == CHANNELS["price_updates"]:
                await self.broadcast_to_type(message, "price")
            elif channel in [CHANNELS["stock_alerts"], CHANNELS["price_alerts"]]:
                await self.broadcast_to_type(message, "alerts")
            elif channel == CHANNELS["system_notifications"]:
                await self.broadcast_to_all(message)
            
        except json.JSONDecodeError:
            logger.warning("Received invalid JSON message from Redis", 
                          channel=channel, message=message_data)
        except Exception as e:
            logger.error("Error handling Redis message", 
                        channel=channel, error=str(e))
    
    async def send_inventory_update(self, inventory_data: Dict[str, Any]):
        """Send inventory update notification"""
        message = {
            "type": "inventory_update",
            "data": inventory_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Publish to Redis for other services
        await redis_manager.publish_message(CHANNELS["inventory_updates"], message)
        
        # Broadcast directly to connected clients
        await self.broadcast_to_type(message, "inventory")
    
    async def send_price_update(self, price_data: Dict[str, Any]):
        """Send price update notification"""
        message = {
            "type": "price_update",
            "data": price_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Publish to Redis for other services
        await redis_manager.publish_message(CHANNELS["price_updates"], message)
        
        # Broadcast directly to connected clients
        await self.broadcast_to_type(message, "price")
    
    async def send_stock_alert(self, alert_data: Dict[str, Any]):
        """Send stock level alert"""
        message = {
            "type": "stock_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": alert_data.get("alert_level", "info")
        }
        
        # Publish to Redis for other services
        await redis_manager.publish_message(CHANNELS["stock_alerts"], message)
        
        # Broadcast to alert connections
        await self.broadcast_to_type(message, "alerts")
    
    async def send_price_alert(self, alert_data: Dict[str, Any]):
        """Send price change alert"""
        message = {
            "type": "price_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": alert_data.get("alert_type", "info")
        }
        
        # Publish to Redis for other services
        await redis_manager.publish_message(CHANNELS["price_alerts"], message)
        
        # Broadcast to alert connections
        await self.broadcast_to_type(message, "alerts")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection statistics"""
        return {
            "total_connections": sum(len(conns) for conns in self.active_connections.values()),
            "connections_by_type": {
                conn_type: len(conns) for conn_type, conns in self.active_connections.items()
            },
            "is_redis_listening": self.is_listening,
            "subscriber_task_running": self.subscriber_task and not self.subscriber_task.done()
        }