# ==============================================================================
# AJOUTS À models/schemas.py - Schémas pour Préférences Utilisateur
# ==============================================================================
# Ajouter ces classes à la fin du fichier models/schemas.py existant

from typing import List

# ==============================================================================
# USER PREFERENCES
# ==============================================================================

class UserPreferences(BaseModel):
    user_id: UUID
    theme: str = "light"  # light, dark
    language: str = "fr"  # fr, en
    currency: str = "XOF"  # XOF, EUR, USD
    email_notifications: bool = True
    push_notifications: bool = True
    default_chart_period: str = "1M"  # 1D, 1W, 1M, 3M, 6M, 1Y
    favorite_sectors: List[str] = []
    risk_profile: str = "moderate"  # conservative, moderate, aggressive
    investment_horizon: str = "medium"  # short, medium, long
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserPreferencesUpdate(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    currency: Optional[str] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    default_chart_period: Optional[str] = None
    favorite_sectors: Optional[List[str]] = None
    risk_profile: Optional[str] = None
    investment_horizon: Optional[str] = None
