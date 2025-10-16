# ==============================================================================
# AJOUTS AU ROUTER: COMPANIES - Sociétés comparables
# ==============================================================================
# Ajouter ces fonctions au fichier api/routers/companies.py existant

# ==============================================================================
# SOCIÉTÉS COMPARABLES (PEERS)
# ==============================================================================

@router.get("/{symbol}/comparable")
async def get_comparable_companies(
    symbol: str,
    limit: int = Query(default=5, ge=1, le=20),
    current_user = Depends(get_current_user)
):
    """
    Trouver les sociétés comparables (même secteur, capitalisation similaire)
    
    - **symbol**: Symbole de la société de référence
    - **limit**: Nombre de sociétés comparables à retourner
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
            # Récupérer les infos de la société de référence
            cur.execute("""
                SELECT c.sector, hd.price, hd.volume
                FROM companies c
                LEFT JOIN LATERAL (
                    SELECT price, volume FROM historical_data
                    WHERE company_id = c.id
                    ORDER BY trade_date DESC
                    LIMIT 1
                ) hd ON TRUE
                WHERE c.symbol = %s
            """, (symbol.upper(),))
            
            ref_company = cur.fetchone()
            
            if not ref_company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Société {symbol} non trouvée"
                )
            
            ref_sector, ref_price, ref_volume = ref_company
            
            if not ref_sector:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Secteur non défini pour {symbol}"
                )
            
            # Trouver les sociétés comparables
            # Critères: même secteur + prix/volume similaires
            cur.execute("""
                WITH company_metrics AS (
                    SELECT 
                        c.id,
                        c.symbol,
                        c.name,
                        c.sector,
                        hd_current.price as current_price,
                        hd_current.volume,
                        hd_prev.price as prev_price,
                        ((hd_current.price - hd_prev.price) / hd_prev.price * 100) as price_change_percent,
                        ta.mm_decision,
                        ta.rsi_decision,
                        ABS(hd_current.price - %s) as price_diff,
                        ABS(COALESCE(hd_current.volume, 0) - COALESCE(%s, 0)) as volume_diff
                    FROM companies c
                    LEFT JOIN LATERAL (
                        SELECT price, volume FROM historical_data
                        WHERE company_id = c.id
                        ORDER BY trade_date DESC
                        LIMIT 1
                    ) hd_current ON TRUE
                    LEFT JOIN LATERAL (
                        SELECT price FROM historical_data
                        WHERE company_id = c.id
                        ORDER BY trade_date DESC
                        OFFSET 1
                        LIMIT 1
                    ) hd_prev ON TRUE
                    LEFT JOIN LATERAL (
                        SELECT mm_decision, rsi_decision FROM technical_analysis ta2
                        JOIN historical_data hd2 ON ta2.historical_data_id = hd2.id
                        WHERE hd2.company_id = c.id
                        ORDER BY hd2.trade_date DESC
                        LIMIT 1
                    ) ta ON TRUE
                    WHERE c.sector = %s
                    AND c.symbol != %s
                    AND hd_current.price IS NOT NULL
                )
                SELECT 
                    symbol,
                    name,
                    sector,
                    current_price,
                    volume,
                    price_change_percent,
                    mm_decision,
                    rsi_decision,
                    price_diff,
                    volume_diff,
                    (price_diff + (volume_diff / 1000.0)) as similarity_score
                FROM company_metrics
                ORDER BY similarity_score ASC
                LIMIT %s
            """, (ref_price or 0, ref_volume or 0, ref_sector, symbol.upper(), limit))
            
            comparable = cur.fetchall()
            
            return {
                "reference_company": symbol,
                "reference_sector": ref_sector,
                "reference_price": float(ref_price) if ref_price else None,
                "comparable_companies": [
                    {
                        "symbol": c[0],
                        "name": c[1],
                        "sector": c[2],
                        "current_price": float(c[3]),
                        "volume": c[4],
                        "price_change_percent": float(c[5]) if c[5] else 0,
                        "mm_decision": c[6],
                        "rsi_decision": c[7],
                        "similarity_score": float(c[10])
                    }
                    for c in comparable
                ]
            }
    
    finally:
        conn.close()


# ==============================================================================
# ANALYSE COMPARATIVE DÉTAILLÉE
# ==============================================================================

@router.get("/{symbol}/compare-with/{peer_symbol}")
async def compare_two_companies(
    symbol: str,
    peer_symbol: str,
    period: Optional[str] = Query(default="3M", regex="^(1M|3M|6M|1Y)$"),
    current_user = Depends(get_current_user)
):
    """
    Comparer deux sociétés en détail
    
    - **symbol**: Première société
    - **peer_symbol**: Société à comparer
    - **period**: Période de comparaison (1M, 3M, 6M, 1Y)
    """
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    
    try:
        period_days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}
        days = period_days[period]
        
        with conn.cursor() as cur:
            # Données comparatives pour les deux sociétés
            query = """
                WITH company_stats AS (
                    SELECT 
                        c.symbol,
                        c.name,
                        c.sector,
                        (SELECT price FROM historical_data 
                         WHERE company_id = c.id 
                         AND trade_date >= CURRENT_DATE - INTERVAL '%s days'
                         ORDER BY trade_date ASC LIMIT 1) as start_price,
                        (SELECT price FROM historical_data 
                         WHERE company_id = c.id 
                         ORDER BY trade_date DESC LIMIT 1) as current_price,
                        (SELECT AVG(volume) FROM historical_data 
                         WHERE company_id = c.id 
                         AND trade_date >= CURRENT_DATE - INTERVAL '%s days') as avg_volume,
                        (SELECT mm_decision FROM technical_analysis ta
                         JOIN historical_data hd ON ta.historical_data_id = hd.id
                         WHERE hd.company_id = c.id
                         ORDER BY hd.trade_date DESC LIMIT 1) as mm_decision,
                        (SELECT rsi FROM technical_analysis ta
                         JOIN historical_data hd ON ta.historical_data_id = hd.id
                         WHERE hd.company_id = c.id
                         ORDER BY hd.trade_date DESC LIMIT 1) as rsi
                    FROM companies c
                    WHERE c.symbol IN (%s, %s)
                )
                SELECT 
                    symbol,
                    name,
                    sector,
                    start_price,
                    current_price,
                    ((current_price - start_price) / start_price * 100) as performance,
                    avg_volume,
                    mm_decision,
                    rsi
                FROM company_stats;
            """
            
            cur.execute(query, (days, days, symbol.upper(), peer_symbol.upper()))
            results = cur.fetchall()
            
            if len(results) < 2:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Une ou plusieurs sociétés introuvables"
                )
            
            company1 = {
                "symbol": results[0][0],
                "name": results[0][1],
                "sector": results[0][2],
                "start_price": float(results[0][3]) if results[0][3] else 0,
                "current_price": float(results[0][4]) if results[0][4] else 0,
                "performance": float(results[0][5]) if results[0][5] else 0,
                "avg_volume": int(results[0][6]) if results[0][6] else 0,
                "mm_decision": results[0][7],
                "rsi": float(results[0][8]) if results[0][8] else None
            }
            
            company2 = {
                "symbol": results[1][0],
                "name": results[1][1],
                "sector": results[1][2],
                "start_price": float(results[1][3]) if results[1][3] else 0,
                "current_price": float(results[1][4]) if results[1][4] else 0,
                "performance": float(results[1][5]) if results[1][5] else 0,
                "avg_volume": int(results[1][6]) if results[1][6] else 0,
                "mm_decision": results[1][7],
                "rsi": float(results[1][8]) if results[1][8] else None
            }
            
            # Analyse comparative
            performance_diff = company1["performance"] - company2["performance"]
            volume_diff_pct = ((company1["avg_volume"] - company2["avg_volume"]) / 
                              company2["avg_volume"] * 100) if company2["avg_volume"] > 0 else 0
            
            return {
                "period": period,
                "company1": company1,
                "company2": company2,
                "comparison": {
                    "performance_difference": performance_diff,
                    "better_performer": company1["symbol"] if performance_diff > 0 else company2["symbol"],
                    "volume_difference_percent": volume_diff_pct,
                    "same_sector": company1["sector"] == company2["sector"],
                    "recommendation": (
                        f"{company1['symbol']} surperforme {company2['symbol']} de {abs(performance_diff):.2f}%"
                        if performance_diff > 0
                        else f"{company2['symbol']} surperforme {company1['symbol']} de {abs(performance_diff):.2f}%"
                    )
                }
            }
    
    finally:
        conn.close()
