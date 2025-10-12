# ==============================================================================
# ROUTER: ANALYSIS - Analyses techniques et fondamentales
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
import psycopg2

from api.config import settings
from models.schemas import TechnicalAnalysis, SignalResponse
from utils.security import get_current_user

router = APIRouter()

@router.get("/{symbol}/technical", response_model=TechnicalAnalysis)
async def get_technical_analysis(
    symbol: str,
    current_user = Depends(get_current_user)
):
    """Récupérer l'analyse technique d'une société"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT hd.trade_date, ta.mm5, ta.mm10, ta.mm20, ta.mm50, ta.mm_decision,
                       ta.bollinger_central, ta.bollinger_inferior, ta.bollinger_superior, ta.bollinger_decision,
                       ta.macd_line, ta.signal_line, ta.histogram, ta.macd_decision,
                       ta.rsi, ta.rsi_decision, ta.stochastic_k, ta.stochastic_d, ta.stochastic_decision
                FROM technical_analysis ta
                JOIN historical_data hd ON ta.historical_data_id = hd.id
                JOIN companies c ON hd.company_id = c.id
                WHERE c.symbol = %s
                ORDER BY hd.trade_date DESC
                LIMIT 1
            """, (symbol.upper(),))
            
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail=f"Analyse technique non disponible pour {symbol}")
            
            return TechnicalAnalysis(
                date=result[0], mm5=result[1], mm10=result[2], mm20=result[3], mm50=result[4], mm_decision=result[5],
                bollinger_central=result[6], bollinger_inferior=result[7], bollinger_superior=result[8], bollinger_decision=result[9],
                macd_line=result[10], signal_line=result[11], histogram=result[12], macd_decision=result[13],
                rsi=result[14], rsi_decision=result[15], stochastic_k=result[16], stochastic_d=result[17], stochastic_decision=result[18]
            )
    finally:
        conn.close()

@router.get("/{symbol}/signals", response_model=SignalResponse)
async def get_trading_signals(symbol: str, current_user = Depends(get_current_user)):
    """Obtenir les signaux d'achat/vente agrégés"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ta.mm_decision, ta.bollinger_decision, ta.macd_decision, ta.rsi_decision, ta.stochastic_decision
                FROM technical_analysis ta
                JOIN historical_data hd ON ta.historical_data_id = hd.id
                JOIN companies c ON hd.company_id = c.id
                WHERE c.symbol = %s
                ORDER BY hd.trade_date DESC
                LIMIT 1
            """, (symbol.upper(),))
            
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Signaux non disponibles")
            
            # Calculer le signal global
            buy_signals = sum(1 for d in result if d and "Achat" in str(d))
            sell_signals = sum(1 for d in result if d and "Vente" in str(d))
            
            if buy_signals > sell_signals:
                overall = "Achat"
                strength = int((buy_signals / 5) * 100)
            elif sell_signals > buy_signals:
                overall = "Vente"
                strength = int((sell_signals / 5) * 100)
            else:
                overall = "Neutre"
                strength = 50
            
            # Récupérer l'analyse complète
            tech_analysis = await get_technical_analysis(symbol, current_user)
            
            return SignalResponse(
                symbol=symbol,
                overall_signal=overall,
                signal_strength=strength,
                indicators=tech_analysis,
                recommendation=f"{overall} - Force: {strength}%"
            )
    finally:
        conn.close()

@router.get("/{symbol}/fundamental")
async def get_fundamental_analysis(symbol: str, current_user = Depends(get_current_user)):
    """Récupérer les analyses fondamentales IA"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT fa.report_title, fa.report_date, fa.analysis_summary, fa.report_url
                FROM fundamental_analysis fa
                JOIN companies c ON fa.company_id = c.id
                WHERE c.symbol = %s
                ORDER BY fa.report_date DESC
                LIMIT 5
            """, (symbol.upper(),))
            
            analyses = cur.fetchall()
            
            return {
                "symbol": symbol,
                "analyses_count": len(analyses),
                "latest_analyses": [
                    {
                        "title": a[0],
                        "date": a[1],
                        "summary": a[2],
                        "url": a[3]
                    }
                    for a in analyses
                ]
            }
    finally:
        conn.close()
