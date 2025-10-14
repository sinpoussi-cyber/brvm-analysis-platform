# ==============================================================================
# BRVM ANALYSIS PLATFORM API - Point d'entrée principal
# ==============================================================================

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time

from api.config import settings
from api.routers import auth, companies, market, analysis, predictions, portfolios, watchlists, alerts

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Créer l'application FastAPI
app = FastAPI(
    title="BRVM Analysis Platform API",
    description="API REST complète pour l'analyse financière de la BRVM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Ajouter le rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware pour mesurer le temps de réponse
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Inclure les routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"])
app.include_router(market.router, prefix="/api/v1/market", tags=["Market Data"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["Predictions"])
app.include_router(portfolios.router, prefix="/api/v1/portfolios", tags=["Portfolios"])
app.include_router(watchlists.router, prefix="/api/v1/watchlists", tags=["Watchlists"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])

# Route racine
@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "BRVM Analysis Platform API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "health": "/health"
    }

# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

# Route pour tester l'authentification
@app.get("/api/v1/test", tags=["Test"])
@limiter.limit("10/minute")
async def test_endpoint(request: Request):
    return {
        "message": "API fonctionnelle!",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
