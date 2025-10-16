# ==============================================================================
# ROUTER: USERS - Préférences utilisateur
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
import psycopg2
import json

from api.config import settings
from models.schemas import UserPreferences, UserPreferencesUpdate
from utils.security import get_current_user

router = APIRouter()

# ==============================================================================
# RÉCUPÉRER LES PRÉFÉRENCES
# ==============================================================================

@router.get("/preferences", response_model=UserPreferences)
async def get_user_preferences(current_user = Depends(get_current_user)):
    """
    Récupérer les préférences de l'utilisateur connecté
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
                    theme,
                    language,
                    currency,
                    email_notifications,
                    push_notifications,
                    default_chart_period,
                    favorite_sectors,
                    risk_profile,
                    investment_horizon,
                    created_at,
                    updated_at
                FROM user_preferences
                WHERE user_id = %s
            """, (str(current_user.id),))
            
            prefs = cur.fetchone()
            
            if not prefs:
                # Créer des préférences par défaut si n'existent pas
                cur.execute("""
                    INSERT INTO user_preferences (user_id)
                    VALUES (%s)
                    RETURNING 
                        theme, language, currency, email_notifications,
                        push_notifications, default_chart_period, favorite_sectors,
                        risk_profile, investment_horizon, created_at, updated_at
                """, (str(current_user.id),))
                
                prefs = cur.fetchone()
                conn.commit()
            
            return UserPreferences(
                user_id=current_user.id,
                theme=prefs[0],
                language=prefs[1],
                currency=prefs[2],
                email_notifications=prefs[3],
                push_notifications=prefs[4],
                default_chart_period=prefs[5],
                favorite_sectors=prefs[6] if prefs[6] else [],
                risk_profile=prefs[7],
                investment_horizon=prefs[8],
                created_at=prefs[9],
                updated_at=prefs[10]
            )
    
    finally:
        conn.close()


# ==============================================================================
# METTRE À JOUR LES PRÉFÉRENCES
# ==============================================================================

@router.put("/preferences")
async def update_user_preferences(
    preferences: UserPreferencesUpdate,
    current_user = Depends(get_current_user)
):
    """
    Mettre à jour les préférences de l'utilisateur
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
            # Construire dynamiquement la requête UPDATE
            update_fields = []
            update_values = []
            
            if preferences.theme is not None:
                update_fields.append("theme = %s")
                update_values.append(preferences.theme)
            
            if preferences.language is not None:
                update_fields.append("language = %s")
                update_values.append(preferences.language)
            
            if preferences.currency is not None:
                update_fields.append("currency = %s")
                update_values.append(preferences.currency)
            
            if preferences.email_notifications is not None:
                update_fields.append("email_notifications = %s")
                update_values.append(preferences.email_notifications)
            
            if preferences.push_notifications is not None:
                update_fields.append("push_notifications = %s")
                update_values.append(preferences.push_notifications)
            
            if preferences.default_chart_period is not None:
                update_fields.append("default_chart_period = %s")
                update_values.append(preferences.default_chart_period)
            
            if preferences.favorite_sectors is not None:
                update_fields.append("favorite_sectors = %s")
                update_values.append(preferences.favorite_sectors)
            
            if preferences.risk_profile is not None:
                update_fields.append("risk_profile = %s")
                update_values.append(preferences.risk_profile)
            
            if preferences.investment_horizon is not None:
                update_fields.append("investment_horizon = %s")
                update_values.append(preferences.investment_horizon)
            
            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Aucune préférence à mettre à jour"
                )
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_values.append(str(current_user.id))
            
            query = f"""
                UPDATE user_preferences
                SET {', '.join(update_fields)}
                WHERE user_id = %s
            """
            
            cur.execute(query, update_values)
            conn.commit()
            
            return {"message": "Préférences mises à jour avec succès"}
    
    finally:
        conn.close()


# ==============================================================================
# RÉINITIALISER LES PRÉFÉRENCES
# ==============================================================================

@router.post("/preferences/reset")
async def reset_user_preferences(current_user = Depends(get_current_user)):
    """
    Réinitialiser les préférences aux valeurs par défaut
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
                UPDATE user_preferences
                SET 
                    theme = 'light',
                    language = 'fr',
                    currency = 'XOF',
                    email_notifications = true,
                    push_notifications = true,
                    default_chart_period = '1M',
                    favorite_sectors = ARRAY[]::VARCHAR[],
                    risk_profile = 'moderate',
                    investment_horizon = 'medium',
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (str(current_user.id),))
            
            conn.commit()
            
            return {"message": "Préférences réinitialisées aux valeurs par défaut"}
    
    finally:
        conn.close()
