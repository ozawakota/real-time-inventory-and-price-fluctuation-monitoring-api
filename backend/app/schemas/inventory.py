"""
Inventory Pydantic schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class InventoryBase(BaseModel):
    """Base inventory schema"""
    sku: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    
    weight: Optional[float] = Field(None, gt=0)
    dimensions: Optional[str] = Field(None, max_length=100)
    
    cost_price: float = Field(0.0, ge=0)
    min_stock_level: int = Field(10, ge=0)
    max_stock_level: int = Field(1000, gt=0)
    
    is_active: bool = True
    is_trackable: bool = True


class InventoryCreate(InventoryBase):
    """Schema for creating inventory items"""
    stock_quantity: int = Field(0, ge=0)
    reserved_quantity: int = Field(0, ge=0)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sku": "PROD-001",
                "name": "Premium Wireless Headphones",
                "description": "High-quality noise-cancelling wireless headphones",
                "category": "Electronics",
                "stock_quantity": 50,
                "reserved_quantity": 5,
                "weight": 250.0,
                "dimensions": "20cm x 18cm x 8cm",
                "cost_price": 8000.0,
                "min_stock_level": 10,
                "max_stock_level": 200,
                "is_active": True,
                "is_trackable": True
            }
        }
    )


class InventoryUpdate(BaseModel):
    """Schema for updating inventory items"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    
    stock_quantity: Optional[int] = Field(None, ge=0)
    reserved_quantity: Optional[int] = Field(None, ge=0)
    
    weight: Optional[float] = Field(None, gt=0)
    dimensions: Optional[str] = Field(None, max_length=100)
    
    cost_price: Optional[float] = Field(None, ge=0)
    min_stock_level: Optional[int] = Field(None, ge=0)
    max_stock_level: Optional[int] = Field(None, gt=0)
    
    is_active: Optional[bool] = None
    is_trackable: Optional[bool] = None


class InventoryResponse(InventoryBase):
    """Schema for inventory responses"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "sku": "PROD-001",
                "name": "Premium Wireless Headphones",
                "description": "High-quality noise-cancelling wireless headphones",
                "category": "Electronics",
                "stock_quantity": 45,
                "reserved_quantity": 3,
                "available_quantity": 42,
                "weight": 250.0,
                "dimensions": "20cm x 18cm x 8cm",
                "cost_price": 8000.0,
                "min_stock_level": 10,
                "max_stock_level": 200,
                "is_active": True,
                "is_trackable": True,
                "is_low_stock": False,
                "stock_status": "in_stock",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )
    
    id: int
    stock_quantity: int
    reserved_quantity: int
    available_quantity: int
    
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    is_low_stock: bool = False
    stock_status: str = "in_stock"


class InventoryStockAlert(BaseModel):
    """Schema for stock alerts"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    sku: str
    name: str
    current_stock: int
    min_stock_level: int
    shortage_amount: int
    alert_level: str  # "low", "critical", "out_of_stock"