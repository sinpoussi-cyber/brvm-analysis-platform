# ==============================================================================
# ROUTER: USERS - Préférences utilisateur
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
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
            # Vérifier si la table user_preferences existe
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_preferences'
                );
            """)
            
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                # Créer la table si elle n'existe pas
                cur.execute("""
                    CREATE TABLE user_preferences (
                        id SERIAL PRIMARY KEY,
                        user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                        theme VARCHAR(20) DEFAULT 'light',
                        language VARCHAR(10) DEFAULT 'fr',
                        notifications_enabled BOOLEAN DEFAULT true,
                        email_notifications BOOLEAN DEFAULT true,
                        sms_notifications BOOLEAN DEFAULT false,
                        push_notifications BOOLEAN DEFAULT true,
                        default_currency VARCHAR(10) DEFAULT 'XOF',
                        favorite_sectors TEXT[] DEFAULT '{}',
                        watchlist_view VARCHAR(20) DEFAULT 'grid',
                        chart_type VARCHAR(20) DEFAULT 'candlestick',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE INDEX idx_user_preferences_user ON user_preferences(user_id);
                """)
                conn.commit()
            
            # Récupérer ou créer les préférences
            cur.execute("""
                INSERT INTO user_preferences (user_id)
                VALUES (%s)
                ON CONFLICT (user_id) DO NOTHING
                RETURNING id;
            """, (str(current_user.id),))
            conn.commit()
            
            # Récupérer les préférences
            cur.execute("""
                SELECT 
                    theme,
                    language,
                    notifications_enabled,
                    email_notifications,
                    sms_notifications,
                    push_notifications,
                    default_currency,
                    favorite_sectors,
                    watchlist_view,
                    chart_type,
                    updated_at
                FROM user_preferences
                WHERE user_id = %s
            """, (str(current_user.id),))
            
            prefs = cur.fetchone()
            
            if not prefs:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Préférences non trouvées"
                )
            
            return UserPreferences(
                theme=prefs[0],
                language=prefs[1],
                notifications_enabled=prefs[2],
                email_notifications=prefs[3],
                sms_notifications=prefs[4],
                push_notifications=prefs[5],
                default_currency=prefs[6],
                favorite_sectors=prefs[7] or [],
                watchlist_view=prefs[8],
                chart_type=prefs[9],
                updated_at=prefs[10]
            )
    
    finally:
        conn.close()

# ==============================================================================
# METTRE À JOUR LES PRÉFÉRENCES
# ==============================================================================

@router.put("/preferences", response_model=UserPreferences)
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
            # Construire la requête dynamiquement
            update_fields = []
            params = []
            
            if preferences.theme is not None:
                update_fields.append("theme = %s")
                params.append(preferences.theme)
            
            if preferences.language is not None:
                update_fields.append("language = %s")
                params.append(preferences.language)
            
            if preferences.notifications_enabled is not None:
                update_fields.append("notifications_enabled = %s")
                params.append(preferences.notifications_enabled)
            
            if preferences.email_notifications is not None:
                update_fields.append("email_notifications = %s")
                params.append(preferences.email_notifications)
            
            if preferences.sms_notifications is not None:
                update_fields.append("sms_notifications = %s")
                params.append(preferences.sms_notifications)
            
            if preferences.push_notifications is not None:
                update_fields.append("push_notifications = %s")
                params.append(preferences.push_notifications)
            
            if preferences.default_currency is not None:
                update_fields.append("default_currency = %s")
                params.append(preferences.default_currency)
            
            if preferences.favorite_sectors is not None:
                update_fields.append("favorite_sectors = %s")
                params.append(preferences.favorite_sectors)
            
            if preferences.watchlist_view is not None:
                update_fields.append("watchlist_view = %s")
                params.append(preferences.watchlist_view)
            
            if preferences.chart_type is not None:
                update_fields.append("chart_type = %s")
                params.append(preferences.chart_type)
            
            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Aucune préférence à mettre à jour"
                )
            
            # Ajouter updated_at
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(str(current_user.id))
            
            query = f"""
                UPDATE user_preferences
                SET {', '.join(update_fields)}
                WHERE user_id = %s
                RETURNING 
                    theme, language, notifications_enabled,
                    email_notifications, sms_notifications, push_notifications,
                    default_currency, favorite_sectors, watchlist_view,
                    chart_type, updated_at
            """
            
            cur.execute(query, params)
            updated = cur.fetchone()
            conn.commit()
            
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Préférences non trouvées"
                )
            
            return UserPreferences(
                theme=updated[0],
                language=updated[1],
                notifications_enabled=updated[2],
                email_notifications=updated[3],
                sms_notifications=updated[4],
                push_notifications=updated[5],
                default_currency=updated[6],
                favorite_sectors=updated[7] or [],
                watchlist_view=updated[8],
                chart_type=updated[9],
                updated_at=updated[10]
            )
    
    finally:
        conn.close()

# ==============================================================================
# RÉINITIALISER LES PRÉFÉRENCES
# ==============================================================================

@router.post("/preferences/reset", response_model=UserPreferences)
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
                    notifications_enabled = true,
                    email_notifications = true,
                    sms_notifications = false,
                    push_notifications = true,
                    default_currency = 'XOF',
                    favorite_sectors = '{}',
                    watchlist_view = 'grid',
                    chart_type = 'candlestick',
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                RETURNING 
                    theme, language, notifications_enabled,
                    email_notifications, sms_notifications, push_notifications,
                    default_currency, favorite_sectors, watchlist_view,
                    chart_type, updated_at
            """, (str(current_user.id),))
            
            reset = cur.fetchone()
            conn.commit()
            
            if not reset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Préférences non trouvées"
                )
            
            return UserPreferences(
                theme=reset[0],
                language=reset[1],
                notifications_enabled=reset[2],
                email_notifications=reset[3],
                sms_notifications=reset[4],
                push_notifications=reset[5],
                default_currency=reset[6],
                favorite_sectors=reset[7] or [],
                watchlist_view=reset[8],
                chart_type=reset[9],
                updated_at=reset[10]
            )
    
    finally:
        conn.close()
