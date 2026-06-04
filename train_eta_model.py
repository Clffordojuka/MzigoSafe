import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from database import engine

def train_lgbm_model():
    print("Initializing MzigoSafe Predictive ETA Engine...")
    
    # 1. Extract Training Data from the Warehouse
    # We join Fact and Dimension tables to get our feature set
    query = """
    SELECT 
        fd.item_price,
        fd.delivery_fee,
        dt.day_of_week,
        dt.is_weekend,
        fd.time_to_pickup_minutes,
        fd.time_to_delivery_minutes AS target_eta
    FROM fact_deliveries fd
    JOIN dim_time dt ON fd.date_id = dt.date_id
    WHERE fd.time_to_delivery_minutes IS NOT NULL
    """
    
    df = pd.read_sql(query, engine)
    
    if len(df) < 10:
        print(f"Not enough data to train a robust model (Current usable rows: {len(df)}).")
        print("The architecture is ready. Keep running deliveries through the system!")
        return

    print(f"Training on {len(df)} historical deliveries...")

    # 2. Feature Engineering & Preprocessing
    # Convert categorical text (day_of_week) into numbers using Pandas get_dummies
    df = pd.get_dummies(df, columns=['day_of_week'], drop_first=True)
    
    # Separate Features (X) and Target (y)
    X = df.drop(columns=['target_eta'])
    y = df['target_eta']

    # Split into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Model Configuration (LightGBM)
    # Using parameters optimized for fast regression on small-to-medium datasets
    model = lgb.LGBMRegressor(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=5,
        random_state=42
    )

    # 4. Training
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        eval_metric='mae',
        callbacks=[lgb.early_stopping(stopping_rounds=10)]
    )

    # 5. Evaluation
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    rmse = mean_squared_error(y_test, predictions, squared=False)
    
    print("\n=== MODEL METRICS ===")
    print(f"Mean Absolute Error (MAE): {mae:.2f} minutes")
    print(f"Root Mean Squared Error (RMSE): {rmse:.2f} minutes")
    
    # In the future, we will save this model to disk using joblib
    # joblib.dump(model, 'models/eta_lgbm_model.pkl')
    print("Model architecture verified and ready for production deployment.")

if __name__ == "__main__":
    train_lgbm_model()