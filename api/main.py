# ==============================================================================
# BRVM ANALYSIS PLATFORM API - Point d'entrée principal
# ==============================================================================

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time

from api.config import settings
from api.database import engine, Base
from api.routers import auth, companies, market, analysis, predictions, portfolios, watchlists, alerts

# Créer les tables si elles n'existent pas
Base.metadata.create_all(bind=engine)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Créer l'application FastAPI
app = FastAPI(
    title="BRVM Analysis Platform API",
