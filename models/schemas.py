# ==============================================================================
# NOUVEAUX SCHÉMAS À AJOUTER À LA FIN DE models/schemas.py
# ==============================================================================

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# ==============================================================================
# USER PREFERENCES - Préférences utilisateur
# ==============================================================================

class UserPreferences(BaseModel):
    """Préférences utilisateur"""
    theme: str = Field(default="light", description="Thème (light/dark)")
    language: str = Field(default="fr", description="Langue (fr/en)")
    notifications_enabled: bool = Field(default=True, description="Notifications activées")
    email_notifications: bool = Field(default=True, description="Notifications par email")
    sms_notifications: bool = Field(default=False, description="Notifications par SMS")
    push_notifications: bool = Field(default=True, description="Notifications push")
    default_currency: str = Field(default="XOF", description="Devise par défaut")
    favorite_sectors: List[str] = Field(default=[], description="Secteurs favoris")
    watchlist_view: str = Field(default="grid", description="Vue watchlist (grid/list)")
    chart_type: str = Field(default="candlestick", description="Type de graphique")
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class UserPreferencesUpdate(BaseModel):
    """Mise à jour des préférences (tous les champs optionnels)"""
    theme: Optional[str] = Field(None, description="Thème (light/dark)")
    language: Optional[str] = Field(None, description="Langue (fr/en)")
    notifications_enabled: Optional[bool] = Field(None, description="Notifications activées")
    email_notifications: Optional[bool] = Field(None, description="Notifications par email")
    sms_notifications: Optional[bool] = Field(None, description="Notifications par SMS")
    push_notifications: Optional[bool] = Field(None, description="Notifications push")
    default_currency: Optional[str] = Field(None, description="Devise par défaut")
    favorite_sectors: Optional[List[str]] = Field(None, description="Secteurs favoris")
    watchlist_view: Optional[str] = Field(None, description="Vue watchlist (grid/list)")
    chart_type: Optional[str] = Field(None, description="Type de graphique")

# ==============================================================================
# SECTOR PERFORMANCE - Performance par secteur
# ==============================================================================

class SectorPerformance(BaseModel):
    """Performance d'un secteur"""
    sector: str
    company_count: int
    avg_change_percent: float
    max_change_percent: float
    min_change_percent: float
    top_performers: str
    
    model_config = ConfigDict(from_attributes=True)

class SectorPerformanceResponse(BaseModel):
    """Réponse API pour performance des secteurs"""
    period_days: int
    sectors: List[SectorPerformance]

# ==============================================================================
# COMPARABLE COMPANIES - Sociétés comparables
# ==============================================================================

class ComparableCompany(BaseModel):
    """Une société comparable"""
    symbol: str
    name: str
    sector: str
    current_price: float
    change_percent: float
    volume: Optional[int] = None
    mm_decision: Optional[str] = None
    rsi_decision: Optional[str] = None
    similarity_score: float
    
    model_config = ConfigDict(from_attributes=True)

class ComparableCompaniesResponse(BaseModel):
    """Réponse API pour sociétés comparables"""
    symbol: str
    sector: str
    comparable_companies: List[ComparableCompany]
