# ==============================================================================
# ROUTER: COMPANIES - Sociétés cotées
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
