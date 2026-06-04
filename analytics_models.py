from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base

# ==========================================
# DIMENSION TABLES (The descriptive context)
# ==========================================

class DimUser(Base):
    """Stores static user traits for slicing data by user type."""
    __tablename__ = "dim_users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True)
    role = Column(String)  # 'seller', 'buyer', 'rider'
    date_joined = Column(Date)

class DimTime(Base):
    """Allows us to group ML predictions by day of week, month, or season."""
    __tablename__ = "dim_time"
    
    date_id = Column(Integer, primary_key=True, index=True) # e.g., 20260604
    actual_date = Column(Date)
    day_of_week = Column(String) # 'Monday', 'Tuesday'
    is_weekend = Column(Integer) # 1 or 0
    month = Column(Integer)
    year = Column(Integer)

# ==========================================
# FACT TABLE (The metrics and measurements)
# ==========================================

class FactDelivery(Base):
    """The center of the star. Used directly for training the LightGBM models."""
    __tablename__ = "fact_deliveries"
    
    fact_id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys to Dimensions
    delivery_id = Column(Integer, unique=True) # Link back to original OLTP DB
    date_id = Column(Integer, ForeignKey("dim_time.date_id"))
    seller_id = Column(Integer, ForeignKey("dim_users.user_id"))
    rider_id = Column(Integer, ForeignKey("dim_users.user_id"))
    
    # The Metrics (What our ML model will learn from)
    item_price = Column(Float)
    delivery_fee = Column(Float)
    
    # ML Targets (Calculated during the ETL process)
    time_to_pickup_minutes = Column(Float, nullable=True)  # Time from Rider Accept -> Pickup OTP
    time_to_delivery_minutes = Column(Float, nullable=True) # Time from Pickup OTP -> Delivery OTP
    
    status = Column(String) # 'delivered', 'cancelled'