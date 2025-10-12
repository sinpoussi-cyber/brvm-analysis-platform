# ==============================================================================
# ROUTER: ALERTS - Alertes de prix et signaux
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import psycopg2
from uuid import UUID

from api.config import settings
from models.schemas import AlertCreate, Alert
from utils.security import get_current_user

router = APIRouter()

@router.get("/", response_model=List[Alert])
async def get_my_alerts(current_user = Depends(get_current_user)):
    """Liste de mes alertes actives"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_id, company_id, alert_type, threshold_value, is_active, triggered_at, created_at
                FROM alerts
                WHERE user_id = %s AND is_active = true
                ORDER BY created_at DESC
            """, (str(current_user.id),))
            
            alerts = cur.fetchall()
            return [
                Alert(
                    id=a[0], user_id=a[1], company_id=a[2], alert_type=a[3],
                    threshold_value=a[4], is_active=a[5], triggered_at=a[6], created_at=a[7]
                )
                for a in alerts
            ]
    finally:
        conn.close()

@router.post("/", response_model=Alert, status_code=status.HTTP_201_CREATED)
async def create_alert(data: AlertCreate, current_user = Depends(get_current_user)):
    """Créer une alerte"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            # Récupérer le company_id
            cur.execute("SELECT id FROM companies WHERE symbol = %s", (data.symbol.upper(),))
            company = cur.fetchone()
            
            if not company:
                raise HTTPException(status_code=404, detail=f"Société {data.symbol} non trouvée")
            
            # Créer l'alerte
            cur.execute("""
                INSERT INTO alerts (user_id, company_id, alert_type, threshold_value)
                VALUES (%s, %s, %s, %s)
                RETURNING id, user_id, company_id, alert_type, threshold_value, is_active, triggered_at, created_at
            """, (str(current_user.id), company[0], data.alert_type, data.threshold_value))
            
            alert = cur.fetchone()
            conn.commit()
            
            return Alert(
                id=alert[0], user_id=alert[1], company_id=alert[2], alert_type=alert[3],
                threshold_value=alert[4], is_active=alert[5], triggered_at=alert[6], created_at=alert[7]
            )
    finally:
        conn.close()

@router.delete("/{alert_id}")
async def delete_alert(alert_id: UUID, current_user = Depends(get_current_user)):
    """Supprimer une alerte"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM alerts
                WHERE id = %s AND user_id = %s
            """, (str(alert_id), str(current_user.id)))
            
            conn.commit()
            return {"message": "Alerte supprimée"}
    finally:
        conn.close()
