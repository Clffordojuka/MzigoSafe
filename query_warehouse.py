import pandas as pd
from database import engine

def view_warehouse_metrics():
    print("📊 Fetching MzigoSafe Analytics...")
    
    # This is a classic Star Schema SQL JOIN. 
    query = """
    SELECT 
        dt.day_of_week,
        COUNT(fd.fact_id) as total_deliveries,
        SUM(fd.item_price) as total_escrow_volume,
        SUM(fd.delivery_fee) as total_rider_payouts,
        AVG(fd.time_to_pickup_minutes) as avg_pickup_time,
        AVG(fd.time_to_delivery_minutes) as avg_transit_time
    FROM fact_deliveries fd
    JOIN dim_time dt ON fd.date_id = dt.date_id
    GROUP BY dt.day_of_week
    """
    
    # Load directly into a Pandas DataFrame for dashboard analysis
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("Warehouse is empty. Complete a delivery and run the ETL first!")
    else:
        print("\n=== EXECUTIVE DASHBOARD (PANDAS) ===")
        print(df.to_string(index=False))

if __name__ == "__main__":
    view_warehouse_metrics()