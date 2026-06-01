from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
import models

router = APIRouter()

# Tell FastAPI where to look for our HTML files
templates = Jinja2Templates(directory="templates")

@router.get("/")
def read_dashboard(request: Request, db: Session = Depends(get_db)):
    # 1. Total Deliveries count
    total_deliveries = db.query(models.Delivery).count()
    
    # 2. Calculate Live Escrow Volume 
    # (Money is in escrow if it's secured, rider assigned, or in transit)
    active_statuses = [
        models.DeliveryStatus.funds_secured,
        models.DeliveryStatus.rider_assigned,
        models.DeliveryStatus.in_transit
    ]
    
    escrow_volume = db.query(
        func.sum(models.Delivery.item_price + models.Delivery.delivery_fee)
    ).filter(models.Delivery.status.in_(active_statuses)).scalar() or 0.0

    # 3. Get counts for specific statuses
    status_counts = db.query(
        models.Delivery.status, func.count(models.Delivery.delivery_id)
    ).group_by(models.Delivery.status).all()
    
    status_dict = {status.name: count for status, count in status_counts}

    # 4. Fetch the 10 most recent deliveries for the table
    recent_deliveries = db.query(models.Delivery).order_by(models.Delivery.created_at.desc()).limit(10).all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_deliveries": total_deliveries,
        "escrow_volume": escrow_volume,
        "status_dict": status_dict,
        "recent_deliveries": recent_deliveries
    })