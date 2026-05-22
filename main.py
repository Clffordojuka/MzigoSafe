from fastapi import FastAPI
from database import engine
import models
from routers import ussd, payments, sms

# Create the database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MzigoSafe API")

# Register the modular routers
app.include_router(ussd.router, prefix="/api/ussd", tags=["USSD"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(sms.router, prefix="/api/sms", tags=["SMS"])

@app.get("/")
def health_check():
    return {"status": "MzigoSafe is running!"}