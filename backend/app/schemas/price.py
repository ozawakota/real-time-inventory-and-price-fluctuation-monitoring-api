"""
Price Pydantic schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class PriceBase(BaseModel):
    """Base price schema"""
    selling_price: float = Field(..., gt=0)
    cost_price: float = Field(..., ge=0)
    discount_price: Optional[float] = Field(None, gt=0)
    currency: str = Field("JPY", min_length=3, max_length=3)
    
    margin_percent: Optional[float] = None
    markup_percent: Optional[float] = None
    
    is_active: bool = True
    requires_approval: bool = False


class PriceCreate(PriceBase):
    """Schema for creating prices"""
    inventory_id: int = Field(..., gt=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "inventory_id": 1,
                "selling_price": 12000.0,
                "cost_price": 8000.0,
                "discount_price": 10800.0,
                "currency": "JPY",
                "margin_percent": 25.0,
                "markup_percent": 50.0,
                "is_active": True,
                "requires_approval": False
            }
        }


class PriceUpdate(BaseModel):
    """Schema for updating prices"""
    selling_price: Optional[float] = Field(None, gt=0)
    cost_price: Optional[float] = Field(None, ge=0)
    discount_price: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    
    margin_percent: Optional[float] = None
    markup_percent: Optional[float] = None
    
    is_active: Optional[bool] = None
    requires_approval: Optional[bool] = None
    
    change_reason: Optional[str] = Field(None, max_length=255)


class PriceResponse(PriceBase):
    """Schema for price responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    inventory_id: int
    
    effective_from: datetime
    effective_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    final_price: float = 0.0
    calculated_margin: float = 0.0
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "inventory_id": 1,
                "selling_price": 12000.0,
                "cost_price": 8000.0,
                "discount_price": 10800.0,
                "currency": "JPY",
                "margin_percent": 25.0,
                "markup_percent": 50.0,
                "is_active": True,
                "requires_approval": False,
                "final_price": 10800.0,
                "calculated_margin": 25.93,
                "effective_from": "2024-01-01T00:00:00Z",
                "effective_until": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class PriceHistoryResponse(BaseModel):
    """Schema for price history responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    inventory_id: int
    
    old_price: float
    new_price: float
    price_change_percent: Optional[float]
    price_change_amount: Optional[float]
    
    change_reason: Optional[str]
    changed_by: Optional[str]
    change_type: Optional[str]
    notes: Optional[str]
    
    changed_at: datetime
    
    # Computed properties
    is_price_increase: bool = False
    change_significance: str = "minor"


class PriceChangeAlert(BaseModel):
    """Schema for price change alerts"""
    inventory_id: int
    sku: str
    item_name: str
    
    old_price: float
    new_price: float
    change_percent: float
    change_amount: float
    
    alert_type: str  # "significant_increase", "significant_decrease", "major_change"
    timestamp: datetime