# ==============================================================================
# MODÈLES PYDANTIC - Schémas de validation (VERSION COMPLÈTE)
# ==============================================================================

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

# ==============================================================================
# AUTHENTICATION
# ==============================================================================

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    user_type: str = Field(default="retail")
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    user_type: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# COMPANIES
# ==============================================================================

class CompanyBase(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None

class Company(CompanyBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CompanyDetail(Company):
    current_price: Optional[Decimal] = None
    price_change: Optional[Decimal] = None
    price_change_percent: Optional[Decimal] = None
    volume: Optional[int] = None
    market_cap: Optional[Decimal] = None

# ==============================================================================
# MARKET DATA
# ==============================================================================

class PriceData(BaseModel):
    date: date
    price: Decimal
    volume: Optional[int] = None
    value: Optional[Decimal] = None

class QuoteResponse(BaseModel):
    symbol: str
    name: str
    current_price: Decimal
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    volume: Optional[int] = None
    value: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    last_update: datetime

# ==============================================================================
# TECHNICAL ANALYSIS
# ==============================================================================

class TechnicalAnalysis(BaseModel):
    date: date
    mm5: Optional[Decimal] = None
    mm10: Optional[Decimal] = None
    mm20: Optional[Decimal] = None
    mm50: Optional[Decimal] = None
    mm_decision: Optional[str] = None
    bollinger_central: Optional[Decimal] = None
    bollinger_inferior: Optional[Decimal] = None
    bollinger_superior: Optional[Decimal] = None
    bollinger_decision: Optional[str] = None
    macd_line: Optional[Decimal] = None
    signal_line: Optional[Decimal] = None
    histogram: Optional[Decimal] = None
    macd_decision: Optional[str] = None
    rsi: Optional[Decimal] = None
    rsi_decision: Optional[str] = None
    stochastic_k: Optional[Decimal] = None
    stochastic_d: Optional[Decimal] = None
    stochastic_decision: Optional[str] = None

class SignalResponse(BaseModel):
    symbol: str
    overall_signal: str  # "Achat", "Vente", "Neutre"
    signal_strength: int  # 0-100
    indicators: TechnicalAnalysis
    recommendation: str

# ==============================================================================
# PREDICTIONS
# ==============================================================================

class Prediction(BaseModel):
    prediction_date: date
    predicted_price: Decimal
    lower_bound: Optional[Decimal] = None
    upper_bound: Optional[Decimal] = None
    confidence_level: Optional[str] = None

class PredictionResponse(BaseModel):
    symbol: str
    current_price: Decimal
    predictions: List[Prediction]
    average_change_percent: Decimal
    trend: str  # "haussière", "baissière", "stable"

# ==============================================================================
# PORTFOLIOS
# ==============================================================================

class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    type: str = Field(default="virtual")
    initial_capital: Decimal = Field(gt=0)

class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class Portfolio(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    type: str
    initial_capital: Decimal
    current_value: Decimal
    cash_balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PortfolioPerformance(Portfolio):
    gain_loss: Decimal
    gain_loss_percent: Decimal
    holdings_count: int

# ==============================================================================
# HOLDINGS
# ==============================================================================

class HoldingBase(BaseModel):
    company_id: int
    quantity: int = Field(gt=0)
    average_price: Decimal = Field(gt=0)

class Holding(HoldingBase):
    id: UUID
    portfolio_id: UUID
    current_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    gain_loss: Optional[Decimal] = None
    gain_loss_percent: Optional[Decimal] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class HoldingEnriched(Holding):
    symbol: str
    company_name: str
    sector: Optional[str] = None
    mm_decision: Optional[str] = None
    rsi_decision: Optional[str] = None

# ==============================================================================
# TRANSACTIONS
# ==============================================================================

class TransactionCreate(BaseModel):
    symbol: str
    quantity: int = Field(gt=0)
    price: Optional[Decimal] = None  # Si None, utilise le prix actuel

class Transaction(BaseModel):
    id: UUID
    portfolio_id: UUID
    company_id: int
    transaction_type: str
    quantity: int
    price: Decimal
    total_amount: Decimal
    fees: Decimal
    net_amount: Decimal
    transaction_date: datetime
    notes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class TransactionEnriched(Transaction):
    symbol: str
    company_name: str

# ==============================================================================
# WATCHLISTS
# ==============================================================================

class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None

class Watchlist(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    is_default: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class WatchlistItemAdd(BaseModel):
    symbol: str
    notes: Optional[str] = None

# ==============================================================================
# ALERTS
# ==============================================================================

class AlertCreate(BaseModel):
    symbol: str
    alert_type: str  # 'price_above', 'price_below', 'signal_buy', 'signal_sell'
    threshold_value: Optional[Decimal] = None

class Alert(BaseModel):
    id: UUID
    user_id: UUID
    company_id: int
    alert_type: str
    threshold_value: Optional[Decimal] = None
    is_active: bool
    triggered_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AlertEnriched(Alert):
    symbol: str
    company_name: str
    current_price: Optional[Decimal] = None

# ==============================================================================
# PAGINATION
# ==============================================================================

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    page_size: int
    total_pages: int

# ==============================================================================
# USER PREFERENCES - Préférences utilisateur (NOUVEAUX)
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
# SECTOR PERFORMANCE - Performance par secteur (NOUVEAUX)
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
# COMPARABLE COMPANIES - Sociétés comparables (NOUVEAUX)
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
