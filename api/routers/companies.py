# ==============================================================================
# ROUTER: COMPANIES - Sociétés cotées (VERSION COMPLÈTE)
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import psycopg2

from api.config import settings
from models.schemas import Company, CompanyDetail
from utils.security import get_current_user

router = APIRouter()

# ==============================================================================
# LISTE DES SOCIÉTÉS
# ==============================================================================

@router.get("/", response_model=List[CompanyDetail])
async def get_companies(
    sector: Optional[str] = None,
    search: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Récupérer la liste des 46 sociétés cotées à la BRVM
    
    - **sector**: Filtrer par secteur (optionnel)
    - **search**: Rechercher par symbole ou nom (optionnel)
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
            query = """
                SELECT 
                    c.id,
                    c.symbol,
                    c.name,
                    c.sector,
                    c.created_at,
                    hd.price as current_price,
                    (hd.price - hd_prev.price) as price_change,
                    CASE 
                        WHEN hd_prev.price > 0 
                        THEN ((hd.price - hd_prev.price) / hd_prev.price * 100)
                        ELSE 0 
                    END as price_change_percent,
                    hd.volume
                FROM companies c
                LEFT JOIN LATERAL (
                    SELECT price, volume FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    LIMIT 1
                ) hd ON true
                LEFT JOIN LATERAL (
                    SELECT price FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    OFFSET 1
                    LIMIT 1
                ) hd_prev ON true
                WHERE 1=1
            """
            
            params = []
            
            if sector:
                query += " AND c.sector = %s"
                params.append(sector)
            
            if search:
                query += " AND (c.symbol ILIKE %s OR c.name ILIKE %s)"
                params.extend([f"%{search}%", f"%{search}%"])
            
            query += " ORDER BY c.symbol"
            
            cur.execute(query, params)
            companies = cur.fetchall()
            
            result = []
            for company in companies:
                result.append(CompanyDetail(
                    id=company[0],
                    symbol=company[1],
                    name=company[2],
                    sector=company[3],
                    created_at=company[4],
                    current_price=company[5],
                    price_change=company[6],
                    price_change_percent=company[7],
                    volume=company[8]
                ))
            
            return result
    
    finally:
        conn.close()

# ==============================================================================
# DÉTAILS D'UNE SOCIÉTÉ
# ==============================================================================

@router.get("/{symbol}", response_model=CompanyDetail)
async def get_company(
    symbol: str,
    current_user = Depends(get_current_user)
):
    """
    Récupérer les détails d'une société par son symbole
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
                    c.id,
                    c.symbol,
                    c.name,
                    c.sector,
                    c.created_at,
                    hd.price as current_price,
                    (hd.price - hd_prev.price) as price_change,
                    CASE 
                        WHEN hd_prev.price > 0 
                        THEN ((hd.price - hd_prev.price) / hd_prev.price * 100)
                        ELSE 0 
                    END as price_change_percent,
                    hd.volume
                FROM companies c
                LEFT JOIN LATERAL (
                    SELECT price, volume FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    LIMIT 1
                ) hd ON true
                LEFT JOIN LATERAL (
                    SELECT price FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    OFFSET 1
                    LIMIT 1
                ) hd_prev ON true
                WHERE c.symbol = %s
            """, (symbol.upper(),))
            
            company = cur.fetchone()
            
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Société {symbol} non trouvée"
                )
            
            return CompanyDetail(
                id=company[0],
                symbol=company[1],
                name=company[2],
                sector=company[3],
                created_at=company[4],
                current_price=company[5],
                price_change=company[6],
                price_change_percent=company[7],
                volume=company[8]
            )
    
    finally:
        conn.close()

# ==============================================================================
# LISTE DES SECTEURS
# ==============================================================================

@router.get("/sectors/list")
async def get_sectors(current_user = Depends(get_current_user)):
    """
    Récupérer la liste des secteurs avec nombre de sociétés
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
                    sector,
                    COUNT(*) as company_count
                FROM companies
                WHERE sector IS NOT NULL
                GROUP BY sector
                ORDER BY sector
            """)
            
            sectors = cur.fetchall()
            
            return [
                {
                    "sector": sector[0],
                    "company_count": sector[1]
                }
                for sector in sectors
            ]
    
    finally:
        conn.close()

# ==============================================================================
# NOUVEAU : SOCIÉTÉS COMPARABLES
# ==============================================================================

@router.get("/{symbol}/comparable")
async def get_comparable_companies(
    symbol: str,
    limit: int = Query(default=5, ge=1, le=10),
    current_user = Depends(get_current_user)
):
    """
    Récupérer les sociétés comparables (même secteur)
    
    Critères de similarité :
    - Même secteur
    - Taille de capitalisation similaire (± 50%)
    - Performance similaire (± 30%)
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
            # Récupérer les infos de la société cible
            cur.execute("""
                SELECT 
                    c.sector,
                    hd_current.price as current_price,
                    hd_current.volume,
                    (hd_current.price - hd_prev.price) / hd_prev.price * 100 as change_percent
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
                WHERE c.symbol = %s
            """, (symbol.upper(),))
            
            target = cur.fetchone()
            
            if not target:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Société {symbol} non trouvée"
                )
            
            target_sector, target_price, target_volume, target_change = target
            
            # Récupérer les sociétés comparables
            cur.execute("""
                SELECT 
                    c.symbol,
                    c.name,
                    c.sector,
                    hd_current.price as current_price,
                    (hd_current.price - hd_prev.price) / hd_prev.price * 100 as change_percent,
                    hd_current.volume,
                    ta.mm_decision,
                    ta.rsi_decision,
                    -- Score de similarité (0-100)
                    (
                        -- Bonus si même secteur
                        CASE WHEN c.sector = %s THEN 40 ELSE 0 END +
                        -- Similarité de prix (max 30 points)
                        CASE 
                            WHEN hd_current.price BETWEEN %s * 0.5 AND %s * 1.5 
                            THEN 30 - ABS(hd_current.price - %s) / %s * 30
                            ELSE 0 
                        END +
                        -- Similarité de performance (max 30 points)
                        CASE 
                            WHEN (hd_current.price - hd_prev.price) / hd_prev.price * 100 
                                 BETWEEN %s * 0.7 AND %s * 1.3
                            THEN 30
                            ELSE 0
                        END
                    ) as similarity_score
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
                LEFT JOIN LATERAL (
                    SELECT mm_decision, rsi_decision FROM technical_analysis ta
                    JOIN historical_data hd ON ta.historical_data_id = hd.id
                    WHERE hd.company_id = c.id
                    ORDER BY hd.trade_date DESC
                    LIMIT 1
                ) ta ON true
                WHERE c.symbol != %s
                AND c.sector IS NOT NULL
                AND hd_current.price IS NOT NULL
                ORDER BY similarity_score DESC
                LIMIT %s
            """, (
                target_sector,  # Pour le bonus secteur
                target_price, target_price, target_price, target_price,  # Pour similarité prix
                target_change, target_change,  # Pour similarité performance
                symbol.upper(),  # Exclure la société elle-même
                limit
            ))
            
            comparables = cur.fetchall()
            
            return {
                "symbol": symbol.upper(),
                "sector": target_sector,
                "comparable_companies": [
                    {
                        "symbol": c[0],
                        "name": c[1],
                        "sector": c[2],
                        "current_price": float(c[3]) if c[3] else 0,
                        "change_percent": round(float(c[4]), 2) if c[4] else 0,
                        "volume": c[5],
                        "mm_decision": c[6],
                        "rsi_decision": c[7],
                        "similarity_score": round(float(c[8]), 1)
                    }
                    for c in comparables
                ]
            }
    
    finally:
        conn.close()
