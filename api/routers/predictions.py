# ==============================================================================
# ROUTER: PREDICTIONS - Prédictions IA
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException
import psycopg2

from api.config import settings
from models.schemas import Prediction, PredictionResponse
from utils.security import get_current_user

router = APIRouter()

@router.get("/{symbol}", response_model=PredictionResponse)
async def get_predictions(symbol: str, current_user = Depends(get_current_user)):
    """Récupérer les prédictions pour les 20 prochains jours ouvrables"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            # Récupérer le prix actuel
            cur.execute("""
                SELECT hd.price
                FROM historical_data hd
                JOIN companies c ON hd.company_id = c.id
                WHERE c.symbol = %s
                ORDER BY hd.trade_date DESC
                LIMIT 1
            """, (symbol.upper(),))
            
            current = cur.fetchone()
            if not current:
                raise HTTPException(status_code=404, detail=f"Société {symbol} non trouvée")
            
            current_price = current[0]
            
            # Récupérer les prédictions
            cur.execute("""
                SELECT p.prediction_date, p.predicted_price, p.lower_bound, p.upper_bound, p.confidence_level
                FROM predictions p
                JOIN companies c ON p.company_id = c.id
                WHERE c.symbol = %s
                ORDER BY p.prediction_date
            """, (symbol.upper(),))
            
            preds = cur.fetchall()
            
            if not preds:
                raise HTTPException(status_code=404, detail=f"Prédictions non disponibles pour {symbol}")
            
            predictions_list = [
                Prediction(
                    prediction_date=p[0],
                    predicted_price=p[1],
                    lower_bound=p[2],
                    upper_bound=p[3],
                    confidence_level=p[4]
                )
                for p in preds
            ]
            
            # Calculer la variation moyenne
            last_pred = preds[-1][1]  # dernière prédiction
            avg_change = float(((last_pred - current_price) / current_price) * 100)
            
            # Déterminer la tendance
            if avg_change > 2:
                trend = "haussière"
            elif avg_change < -2:
                trend = "baissière"
            else:
                trend = "stable"
            
            return PredictionResponse(
                symbol=symbol,
                current_price=current_price,
                predictions=predictions_list,
                average_change_percent=avg_change,
                trend=trend
            )
    finally:
        conn.close()
