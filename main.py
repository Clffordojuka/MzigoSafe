from fastapi import FastAPI
from database import engine
import models
import analytics_models
from routers import ussd, payments, sms, dashboard, mpesa

# Create the database tables on startup
models.Base.metadata.create_all(bind=engine)
analytics_models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MzigoSafe API")

# Register the modular routers
app.include_router(ussd.router, prefix="/api/ussd", tags=["USSD"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(sms.router, prefix="/api/sms", tags=["SMS"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(mpesa.router, prefix="/api/mpesa", tags=["M-Pesa API"])

@app.get("/")
def health_check():
    return {"status": "MzigoSafe is running!"}