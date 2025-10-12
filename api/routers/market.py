# ==============================================================================
# ROUTER: MARKET DATA - Données de marché
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime, timedelta
import psycopg2

from api.config import settings
from models.schemas import PriceData, QuoteResponse
from utils.security import get_current_user

router = APIRouter()

# ==============================================================================
# HISTORIQUE DES PRIX
# ==============================================================================

@router.get("/{symbol}/price", response_model=List[PriceData])
async def get_price_history(
    symbol: str,
    days: int = Query(default=100, ge=1, le=1000),
    current_user = Depends(get_current_user)
):
    """
    Récupérer l'historique des prix d'une société
    
    - **symbol**: Symbole de la société (ex: BICC, NTLC)
    - **days**: Nombre de jours d'historique (1-1000, défaut: 100)
    """
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT hd.trade_date, hd.price, hd.volume, hd.value
                FROM historical_data hd
                JOIN companies c ON hd.company_id = c.id
                WHERE c.symbol = %s
                ORDER BY hd.trade_date DESC
                LIMIT %s
            """, (symbol.upper(), days))
            
            prices = cur.fetchall()
            
            if not prices:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Aucune donnée trouvée pour {symbol}"
                )
            
            # Inverser pour avoir du plus ancien au plus récent
            prices.reverse()
            
            return [
                PriceData(
                    date=price[0],
                    price=price[1],
                    volume=price[2],
                    value=price[3]
                )
                for price in prices
            ]
    
    finally:
        conn.close()

# ==============================================================================
# COTATION ACTUELLE
# ==============================================================================

@router.get("/{symbol}/quote", response_model=QuoteResponse)
async def get_quote(
    symbol: str,
    current_user = Depends(get_current_user)
):
    """
    Récupérer la cotation actuelle d'une société
    """
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.symbol,
                    c.name,
                    hd_current.price as current_price,
                    hd_current.volume,
                    hd_current.value,
                    (hd_current.price - hd_prev.price) as change,
                    CASE 
                        WHEN hd_prev.price > 0 
                        THEN ((hd_current.price - hd_prev.price) / hd_prev.price * 100)
                        ELSE 0 
                    END as change_percent,
                    hd_current.trade_date as last_update
                FROM companies c
                LEFT JOIN LATERAL (
                    SELECT price, volume, value, trade_date
                    FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    LIMIT 1
                ) hd_current ON true
                LEFT JOIN LATERAL (
                    SELECT price
                    FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    OFFSET 1
                    LIMIT 1
                ) hd_prev ON true
                WHERE c.symbol = %s
            """, (symbol.upper(),))
            
            quote = cur.fetchone()
            
            if not quote or not quote[2]:  # quote[2] = current_price
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Aucune cotation trouvée pour {symbol}"
                )
            
            return QuoteResponse(
                symbol=quote[0],
                name=quote[1],
                current_price=quote[2],
                volume=quote[3],
                value=quote[4],
                change=quote[5],
                change_percent=quote[6],
                last_update=quote[7]
            )
    
    finally:
        conn.close()

# ==============================================================================
# TOP HAUSSES
# ==============================================================================

@router.get("/gainers/top")
async def get_top_gainers(
    limit: int = Query(default=10, ge=1, le=50),
    current_user = Depends(get_current_user)
):
    """
    Top des hausses du jour
    """
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.symbol,
                    c.name,
                    hd_current.price as current_price,
                    (hd_current.price - hd_prev.price) as change,
                    CASE 
                        WHEN hd_prev.price > 0 
                        THEN ((hd_current.price - hd_prev.price) / hd_prev.price * 100)
                        ELSE 0 
                    END as change_percent,
                    hd_current.volume
                FROM companies c
                LEFT JOIN LATERAL (
                    SELECT price, volume FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    LIMIT 1
                ) hd_current ON true
                LEFT JOIN LATERAL (
                    SELECT price FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    OFFSET 1
                    LIMIT 1
                ) hd_prev ON true
                WHERE hd_current.price IS NOT NULL AND hd_prev.price IS NOT NULL
                ORDER BY change_percent DESC
                LIMIT %s
            """, (limit,))
            
            gainers = cur.fetchall()
            
            return [
                {
                    "symbol": g[0],
                    "name": g[1],
                    "current_price": float(g[2]),
                    "change": float(g[3]) if g[3] else 0,
                    "change_percent": float(g[4]),
                    "volume": g[5]
                }
                for g in gainers
            ]
    
    finally:
        conn.close()

# ==============================================================================
# TOP BAISSES
# ==============================================================================

@router.get("/losers/top")
async def get_top_losers(
    limit: int = Query(default=10, ge=1, le=50),
    current_user = Depends(get_current_user)
):
    """
    Top des baisses du jour
    """
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.symbol,
                    c.name,
                    hd_current.price as current_price,
                    (hd_current.price - hd_prev.price) as change,
                    CASE 
                        WHEN hd_prev.price > 0 
                        THEN ((hd_current.price - hd_prev.price) / hd_prev.price * 100)
                        ELSE 0 
                    END as change_percent,
                    hd_current.volume
                FROM companies c
                LEFT JOIN LATERAL (
                    SELECT price, volume FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    LIMIT 1
                ) hd_current ON true
                LEFT JOIN LATERAL (
                    SELECT price FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    OFFSET 1
                    LIMIT 1
                ) hd_prev ON true
                WHERE hd_current.price IS NOT NULL AND hd_prev.price IS NOT NULL
                ORDER BY change_percent ASC
                LIMIT %s
            """, (limit,))
            
            losers = cur.fetchall()
            
            return [
                {
                    "symbol": l[0],
                    "name": l[1],
                    "current_price": float(l[2]),
                    "change": float(l[3]) if l[3] else 0,
                    "change_percent": float(l[4]),
                    "volume": l[5]
                }
                for l in losers
            ]
    
    finally:
        conn.close()

# ==============================================================================
# TOP VOLUMES
# ==============================================================================

@router.get("/volume/top")
async def get_top_volume(
    limit: int = Query(default=10, ge=1, le=50),
    current_user = Depends(get_current_user)
):
    """
    Top des volumes échangés
    """
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.symbol,
                    c.name,
                    hd.price as current_price,
                    hd.volume,
                    hd.value
                FROM companies c
                LEFT JOIN LATERAL (
                    SELECT price, volume, value FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    LIMIT 1
                ) hd ON true
                WHERE hd.volume IS NOT NULL
                ORDER BY hd.volume DESC
                LIMIT %s
            """, (limit,))
            
            volumes = cur.fetchall()
            
            return [
                {
                    "symbol": v[0],
                    "name": v[1],
                    "current_price": float(v[2]),
                    "volume": v[3],
                    "value": float(v[4]) if v[4] else 0
                }
                for v in volumes
            ]
    
    finally:
        conn.close()
