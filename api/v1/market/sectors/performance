# ==============================================================================
# AJOUTS AU ROUTER: MARKET DATA - Performance par secteur
# ==============================================================================
# Ajouter ces fonctions au fichier api/routers/market.py existant

from typing import Optional
from decimal import Decimal

# ==============================================================================
# PERFORMANCE PAR SECTEUR
# ==============================================================================

@router.get("/sectors/performance")
async def get_sectors_performance(
    period: Optional[str] = Query(default="1M", regex="^(1D|1W|1M|3M|6M|1Y|YTD)$"),
    current_user = Depends(get_current_user)
):
    """
    Récupérer la performance de chaque secteur
    
    - **period**: Période d'analyse (1D, 1W, 1M, 3M, 6M, 1Y, YTD)
    """
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    
    try:
        # Mapper la période en jours
        period_days = {
            "1D": 1,
            "1W": 7,
            "1M": 30,
            "3M": 90,
            "6M": 180,
            "1Y": 365,
            "YTD": None  # Depuis début d'année
        }
        
        days = period_days[period]
        
        with conn.cursor() as cur:
            if period == "YTD":
                # Depuis le début de l'année
                query = """
                    WITH sector_data AS (
                        SELECT 
                            c.sector,
                            c.id as company_id,
                            (
                                SELECT price FROM historical_data
                                WHERE company_id = c.id 
                                AND trade_date >= DATE_TRUNC('year', CURRENT_DATE)
                                ORDER BY trade_date ASC
                                LIMIT 1
                            ) as start_price,
                            (
                                SELECT price FROM historical_data
                                WHERE company_id = c.id
                                ORDER BY trade_date DESC
                                LIMIT 1
                            ) as current_price
                        FROM companies c
                        WHERE c.sector IS NOT NULL
                    )
                    SELECT 
                        sector,
                        COUNT(*) as companies_count,
                        AVG(
                            CASE 
                                WHEN start_price > 0 
                                THEN ((current_price - start_price) / start_price * 100)
                                ELSE 0 
                            END
                        ) as avg_performance,
                        SUM(
                            CASE 
                                WHEN start_price > 0 
                                THEN ((current_price - start_price) / start_price * 100)
                                ELSE 0 
                            END
                        ) as total_performance,
                        AVG(current_price) as avg_current_price
                    FROM sector_data
                    WHERE start_price IS NOT NULL AND current_price IS NOT NULL
                    GROUP BY sector
                    ORDER BY avg_performance DESC;
                """
                cur.execute(query)
            else:
                # Performance sur N jours
                query = """
                    WITH sector_data AS (
                        SELECT 
                            c.sector,
                            c.id as company_id,
                            (
                                SELECT price FROM historical_data
                                WHERE company_id = c.id 
                                AND trade_date >= CURRENT_DATE - INTERVAL '%s days'
                                ORDER BY trade_date ASC
                                LIMIT 1
                            ) as start_price,
                            (
                                SELECT price FROM historical_data
                                WHERE company_id = c.id
                                ORDER BY trade_date DESC
                                LIMIT 1
                            ) as current_price
                        FROM companies c
                        WHERE c.sector IS NOT NULL
                    )
                    SELECT 
                        sector,
                        COUNT(*) as companies_count,
                        AVG(
                            CASE 
                                WHEN start_price > 0 
                                THEN ((current_price - start_price) / start_price * 100)
                                ELSE 0 
                            END
                        ) as avg_performance,
                        SUM(
                            CASE 
                                WHEN start_price > 0 
                                THEN ((current_price - start_price) / start_price * 100)
                                ELSE 0 
                            END
                        ) as total_performance,
                        AVG(current_price) as avg_current_price
                    FROM sector_data
                    WHERE start_price IS NOT NULL AND current_price IS NOT NULL
                    GROUP BY sector
                    ORDER BY avg_performance DESC;
                """
                cur.execute(query, (days,))
            
            sectors = cur.fetchall()
            
            return {
                "period": period,
                "sectors": [
                    {
                        "sector": s[0],
                        "companies_count": s[1],
                        "avg_performance": float(s[2]) if s[2] else 0,
                        "total_performance": float(s[3]) if s[3] else 0,
                        "avg_current_price": float(s[4]) if s[4] else 0,
                        "trend": "haussière" if s[2] and s[2] > 0 else "baissière" if s[2] and s[2] < 0 else "stable"
                    }
                    for s in sectors
                ]
            }
    
    finally:
        conn.close()


# ==============================================================================
# COMPARAISON DE SECTEURS
# ==============================================================================

@router.get("/sectors/compare")
async def compare_sectors(
    sectors: str = Query(..., description="Liste des secteurs séparés par virgule"),
    period: Optional[str] = Query(default="1M", regex="^(1D|1W|1M|3M|6M|1Y)$"),
    current_user = Depends(get_current_user)
):
    """
    Comparer la performance de plusieurs secteurs
    
    - **sectors**: Liste des secteurs (ex: "Banque,Télécommunications,Industrie")
    - **period**: Période de comparaison
    """
    sectors_list = [s.strip() for s in sectors.split(',')]
    
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    
    try:
        period_days = {
            "1D": 1, "1W": 7, "1M": 30,
            "3M": 90, "6M": 180, "1Y": 365
        }
        
        days = period_days[period]
        
        with conn.cursor() as cur:
            # Utiliser ANY pour matcher plusieurs secteurs
            query = """
                WITH sector_performance AS (
                    SELECT 
                        c.sector,
                        c.symbol,
                        c.name,
                        hd_start.price as start_price,
                        hd_current.price as current_price,
                        hd_current.volume,
                        ((hd_current.price - hd_start.price) / hd_start.price * 100) as performance
                    FROM companies c
                    LEFT JOIN LATERAL (
                        SELECT price FROM historical_data
                        WHERE company_id = c.id
                        AND trade_date >= CURRENT_DATE - INTERVAL '%s days'
                        ORDER BY trade_date ASC
                        LIMIT 1
                    ) hd_start ON TRUE
                    LEFT JOIN LATERAL (
                        SELECT price, volume FROM historical_data
                        WHERE company_id = c.id
                        ORDER BY trade_date DESC
                        LIMIT 1
                    ) hd_current ON TRUE
                    WHERE c.sector = ANY(%s)
                    AND hd_start.price IS NOT NULL
                    AND hd_current.price IS NOT NULL
                )
                SELECT 
                    sector,
                    symbol,
                    name,
                    current_price,
                    performance,
                    volume
                FROM sector_performance
                ORDER BY sector, performance DESC;
            """
            
            cur.execute(query, (days, sectors_list))
            results = cur.fetchall()
            
            # Organiser par secteur
            comparison = {}
            for row in results:
                sector = row[0]
                if sector not in comparison:
                    comparison[sector] = {
                        "sector": sector,
                        "companies": [],
                        "avg_performance": 0,
                        "best_performer": None,
                        "worst_performer": None
                    }
                
                company_data = {
                    "symbol": row[1],
                    "name": row[2],
                    "current_price": float(row[3]),
                    "performance": float(row[4]),
                    "volume": row[5]
                }
                
                comparison[sector]["companies"].append(company_data)
            
            # Calculer statistiques par secteur
            for sector, data in comparison.items():
                performances = [c["performance"] for c in data["companies"]]
                data["avg_performance"] = sum(performances) / len(performances)
                data["best_performer"] = max(data["companies"], key=lambda x: x["performance"])
                data["worst_performer"] = min(data["companies"], key=lambda x: x["performance"])
            
            return {
                "period": period,
                "sectors_compared": sectors_list,
                "comparison": list(comparison.values())
            }
    
    finally:
        conn.close()
