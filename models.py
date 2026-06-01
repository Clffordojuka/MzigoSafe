from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.sql import func
import enum
from database import Base

class DeliveryStatus(enum.Enum):
    pending_buyer_payment = "pending_buyer_payment"
    funds_secured = "funds_secured"
    rider_assigned = "rider_assigned"
    in_transit = "in_transit"
    delivered = "delivered"
    cancelled = "cancelled"

class PaymentStatus(enum.Enum):
    initiated = "initiated"
    escrowed = "escrowed"
    released = "released"
    failed = "failed"

class UserRole(enum.Enum):
    seller = "seller"
    buyer = "buyer"
    rider = "rider"

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(15), unique=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    wallet_balance = Column(Numeric(10, 2), default=10000.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Delivery(Base):
    __tablename__ = "deliveries"
    delivery_id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.user_id", ondelete="RESTRICT"))
    buyer_id = Column(Integer, ForeignKey("users.user_id", ondelete="RESTRICT"))
    rider_id = Column(Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=True)
    
    item_price = Column(Numeric(10, 2), nullable=False)
    delivery_fee = Column(Numeric(10, 2), nullable=False)
    pickup_otp = Column(String(4), nullable=True)
    dropoff_otp = Column(String(4), nullable=True)
    
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.pending_buyer_payment)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EscrowLedger(Base):
    __tablename__ = "escrow_ledger"
    ledger_id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.delivery_id", ondelete="RESTRICT"))
    mpesa_checkout_id = Column(String(100), unique=True)
    amount_held = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.initiated)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# NEW: The missing USSD Session Table!
# ==========================================
class UssdSession(Base):
    __tablename__ = "ussd_sessions"
    session_id = Column(String(100), primary_key=True, index=True)
    phone_number = Column(String(15), index=True)
    current_screen = Column(String(50), default="MAIN_MENU")
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())