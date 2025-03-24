from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

# Import module routers
from modules.auth.endpoints import router as auth_router
from modules.billing.endpoints import router as billing_router
from modules.radius.endpoints import router as radius_router
from modules.tariff.endpoints import router as tariff_router
from modules.monitoring.endpoints import router as monitoring_router
from modules.crm.endpoints import router as crm_router
from modules.reseller.endpoints import router as reseller_router
from modules.communications.router import router as communications_router

# Import API Gateway
from backend_core.api_gateway import APIGateway
from backend_core.api_gateway.config import settings as gateway_settings

# Import logging and monitoring services
from backend_core.database import engine
from backend_core.logging_init import init_logging_and_monitoring, shutdown_logging_and_monitoring
from backend_core.config import settings

app = FastAPI(
    title="ISP Management Platform",
    description="Comprehensive ISP management system with billing, AAA, and customer management",
    version="1.0.0"
)

# Initialize API Gateway
api_gateway = APIGateway(app)

# CORS configuration is now handled by the API Gateway

@app.get("/")
async def root():
    return {
        "name": "ISP Management Platform",
        "version": "1.0.0",
        "status": "operational"
    }

# Register module routers with API Gateway
api_gateway.register_service(auth_router, "/api/auth", version="1")
api_gateway.register_service(billing_router, "/api/billing", version="1")
api_gateway.register_service(radius_router, "/api/radius", version="1")
api_gateway.register_service(tariff_router, "/api/tariff", version="1")
api_gateway.register_service(monitoring_router, "/api/monitoring", version="1")
api_gateway.register_service(crm_router, "/api/crm", version="1")
api_gateway.register_service(reseller_router, "/api/reseller", version="1")
api_gateway.register_service(communications_router, "/api/communications", version="1")

# Configure rate limits
for path, config in gateway_settings.RATE_LIMITS.items():
    api_gateway.set_rate_limit(path, config["limit"], config["period"])

# Configure circuit breakers
for path, config in gateway_settings.CIRCUIT_BREAKER_SETTINGS.items():
    api_gateway.configure_circuit_breaker(path, config["threshold"], config["recovery_time"])

# Initialize logging and monitoring services
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    init_logging_and_monitoring(app, engine)

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown services on application shutdown."""
    shutdown_logging_and_monitoring()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
