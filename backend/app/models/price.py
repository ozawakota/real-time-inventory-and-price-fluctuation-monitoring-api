"""
Price database models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Price(Base):
    """Current price model"""
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=False, index=True)
    
    # Price information
    selling_price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=False)
    discount_price = Column(Float, nullable=True)
    currency = Column(String(3), nullable=False, default="JPY")
    
    # Pricing strategy
    margin_percent = Column(Float)  # calculated margin
    markup_percent = Column(Float)  # markup from cost
    
    # Status and validation
    is_active = Column(Boolean, default=True, nullable=False)
    requires_approval = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    effective_from = Column(DateTime(timezone=True), server_default=func.now())
    effective_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Price(id={self.id}, inventory_id={self.inventory_id}, price={self.selling_price})>"
    
    @property
    def final_price(self) -> float:
        """Get the final selling price (considering discounts)"""
        return self.discount_price if self.discount_price else self.selling_price
    
    @property
    def calculated_margin(self) -> float:
        """Calculate profit margin percentage"""
        if self.cost_price <= 0:
            return 0.0
        return ((self.final_price - self.cost_price) / self.final_price) * 100


class PriceHistory(Base):
    """Price change history model"""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=False, index=True)
    
    # Historical price data
    old_price = Column(Float, nullable=False)
    new_price = Column(Float, nullable=False)
    price_change_percent = Column(Float)
    price_change_amount = Column(Float)
    
    # Change context
    change_reason = Column(String(255))
    changed_by = Column(String(100))  # user who made the change
    change_type = Column(String(50))  # manual, automatic, bulk_update, etc.
    
    # Additional context
    notes = Column(Text)
    external_reference = Column(String(255))  # reference to external system
    
    # Timestamps
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<PriceHistory(id={self.id}, inventory_id={self.inventory_id}, {self.old_price}->{self.new_price})>"
    
    @property
    def is_price_increase(self) -> bool:
        """Check if this was a price increase"""
        return self.new_price > self.old_price
    
    @property
    def change_significance(self) -> str:
        """Categorize the significance of price change"""
        abs_change = abs(self.price_change_percent or 0)
        if abs_change >= 20:
            return "major"
        elif abs_change >= 10:
            return "significant"
        elif abs_change >= 5:
            return "moderate"
        else:
            return "minor"