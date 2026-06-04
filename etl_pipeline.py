import os
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import analytics_models

def run_etl():
    db = SessionLocal()
    print("Starting MzigoSafe Nightly ETL Pipeline...")

    try:
        # =====================================================================
        # 1. EXTRACT
        # =====================================================================
        # Get IDs of deliveries we have already warehoused
        processed_ids = [f.delivery_id for f in db.query(analytics_models.FactDelivery.delivery_id).all()]
        
        # Fetch only completed deliveries that are NOT in the Fact table yet
        new_deliveries = db.query(models.Delivery).filter(
            models.Delivery.status == models.DeliveryStatus.delivered,
            models.Delivery.delivery_id.notin_(processed_ids)
        ).all()

        if not new_deliveries:
            print("No new deliveries to process tonight.")
            return

        print(f"Found {len(new_deliveries)} new deliveries. Extracting...")

        for delivery in new_deliveries:
            # =================================================================
            # 2. TRANSFORM & LOAD: DIMENSIONS
            # =================================================================
            
            # A. Date Dimension (dim_time)
            delivery_date = delivery.created_at.date()
            date_id = int(delivery_date.strftime("%Y%m%d")) # e.g., 20260604
            
            dim_time = db.query(analytics_models.DimTime).filter_by(date_id=date_id).first()
            if not dim_time:
                dim_time = analytics_models.DimTime(
                    date_id=date_id,
                    actual_date=delivery_date,
                    day_of_week=delivery_date.strftime("%A"),
                    is_weekend=1 if delivery_date.weekday() >= 5 else 0,
                    month=delivery_date.month,
                    year=delivery_date.year
                )
                db.add(dim_time)
                db.commit() 

            # B. User Dimensions (dim_users for Seller and Rider)
            for user_id in [delivery.seller_id, delivery.rider_id]:
                if user_id:
                    dim_user = db.query(analytics_models.DimUser).filter_by(user_id=user_id).first()
                    if not dim_user:
                        oltp_user = db.query(models.User).filter_by(user_id=user_id).first()
                        if oltp_user:
                            dim_user = analytics_models.DimUser(
                                user_id=oltp_user.user_id,
                                phone_number=oltp_user.phone_number,
                                role=oltp_user.role,
                                date_joined=datetime.now().date() # Simplified for ETL
                            )
                            db.add(dim_user)
            db.commit()

            # =================================================================
            # 3. TRANSFORM: FACT METRICS (The ETA Math)
            # =================================================================
            pickup_mins = None
            delivery_mins = None
            
            # Calculate duration features for the ML target variables
            if hasattr(delivery, 'pickup_time') and delivery.pickup_time:
                pickup_mins = round((delivery.pickup_time - delivery.created_at).total_seconds() / 60.0, 2)
            
            if hasattr(delivery, 'dropoff_time') and delivery.pickup_time and delivery.dropoff_time:
                delivery_mins = round((delivery.dropoff_time - delivery.pickup_time).total_seconds() / 60.0, 2)

            # =================================================================
            # 4. LOAD: FACT TABLE
            # =================================================================
            fact = analytics_models.FactDelivery(
                delivery_id=delivery.delivery_id,
                date_id=date_id,
                seller_id=delivery.seller_id,
                rider_id=delivery.rider_id,
                item_price=float(delivery.item_price),
                delivery_fee=float(delivery.delivery_fee),
                time_to_pickup_minutes=pickup_mins,
                time_to_delivery_minutes=delivery_mins,
                status=delivery.status
            )
            db.add(fact)

        db.commit()
        print(f"ETL Complete! Successfully warehoused {len(new_deliveries)} deliveries.")

    except Exception as e:
        db.rollback()
        print(f"ETL Pipeline Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_etl()