"""
API v1 router configuration
"""
from fastapi import APIRouter

from app.api.v1.endpoints import inventory, price

# Main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    inventory.router,
    prefix="/inventory",
    tags=["inventory"]
)

api_router.include_router(
    price.router,
    prefix="/price",
    tags=["price"]
)