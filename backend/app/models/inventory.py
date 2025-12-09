"""
Inventory database model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class Inventory(Base):
    """Inventory item model"""
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)
    
    # Stock information
    stock_quantity = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, nullable=False, default=0)
    available_quantity = Column(Integer, nullable=False, default=0)
    
    # Physical attributes
    weight = Column(Float)  # in grams
    dimensions = Column(String(100))  # format: "length x width x height"
    
    # Business attributes
    cost_price = Column(Float, nullable=False, default=0.0)
    min_stock_level = Column(Integer, nullable=False, default=10)
    max_stock_level = Column(Integer, nullable=False, default=1000)
    
    # Status and flags
    is_active = Column(Boolean, default=True, nullable=False)
    is_trackable = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Inventory(id={self.id}, sku='{self.sku}', stock={self.stock_quantity})>"
    
    @property
    def is_low_stock(self) -> bool:
        """Check if item is below minimum stock level"""
        return self.available_quantity <= self.min_stock_level
    
    @property
    def stock_status(self) -> str:
        """Get current stock status"""
        if self.available_quantity <= 0:
            return "out_of_stock"
        elif self.is_low_stock:
            return "low_stock"
        else:
            return "in_stock"