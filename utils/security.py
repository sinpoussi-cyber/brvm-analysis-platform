# ==============================================================================
# SÉCURITÉ - JWT, Hashing, Authentication
# ==============================================================================

from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID
import psycopg2

from api.config import settings
from models.schemas import TokenData

# Configuration du hashing de mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ==============================================================================
# FONCTIONS DE HASHING
# ==============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie si un mot de passe correspond au hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash un mot de passe"""
    return pwd_context.hash(password)

# ==============================================================================
# FONCTIONS JWT
# ==============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crée un token JWT d'accès"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Crée un token JWT de rafraîchissement"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt

def decode_token(token: str) -> TokenData:
    """Décode un token JWT"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide"
            )
        
        return TokenData(user_id=UUID(user_id), email=email)
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide"
        )

# ==============================================================================
# CLASSE UTILISATEUR
# ==============================================================================

class User:
    """Classe représentant un utilisateur"""
    def __init__(self, data):
        self.id = data[0]
        self.email = data[1]
        self.user_type = data[2]
        self.first_name = data[3]
        self.last_name = data[4]
        self.is_active = data[5]
        self.is_verified = data[6] if len(data) > 6 else False
        self.created_at = data[7] if len(data) > 7 else None

# ==============================================================================
# DÉPENDANCES FASTAPI
# ==============================================================================

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Récupère l'utilisateur actuel depuis le token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token_data = decode_token(token)
        
        # Récupérer l'utilisateur depuis la DB
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
                    SELECT id, email, user_type, first_name, last_name, is_active, is_verified, created_at
                    FROM users 
                    WHERE id = %s AND is_active = true
                """, (str(token_data.user_id),))
                
                user_data = cur.fetchone()
            
            if user_data is None:
                raise credentials_exception
            
            return User(user_data)
        
        finally:
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erreur lors de la récupération de l'utilisateur: {str(e)}")
        raise credentials_exception

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Vérifie que l'utilisateur est actif"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utilisateur inactif"
        )
    return current_user

# ==============================================================================
# FONCTIONS D'AUTORISATION
# ==============================================================================

def check_user_type(user: User, allowed_types: list):
    """Vérifie que l'utilisateur a le bon type"""
    if user.user_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit pour ce type d'utilisateur"
        )
    return True

def require_user_type(allowed_types: list):
    """
    Décorateur de dépendance pour restreindre l'accès par type d'utilisateur
    
    Usage:
        @router.get("/admin")
        async def admin_endpoint(current_user = Depends(require_user_type(["admin"]))):
            ...
    """
    async def user_type_checker(current_user: User = Depends(get_current_user)):
        check_user_type(current_user, allowed_types)
        return current_user
    
    return user_type_checker
