# ==============================================================================
# ROUTER: AUTHENTICATION
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
import psycopg2

from api.database import get_db
from api.config import settings
from models.schemas import UserRegister, UserLogin, Token, UserResponse
from utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user
)

router = APIRouter()

# ==============================================================================
# INSCRIPTION
# ==============================================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Inscription d'un nouvel utilisateur
    """
    # Connexion directe à PostgreSQL
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            # Vérifier si l'email existe déjà
            cur.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cet email est déjà utilisé"
                )
            
            # Hasher le mot de passe
            hashed_password = get_password_hash(user_data.password)
            
            # Insérer le nouvel utilisateur
            cur.execute("""
                INSERT INTO users (email, password_hash, user_type, first_name, last_name, phone)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, email, user_type, first_name, last_name, is_active, is_verified, created_at
            """, (
                user_data.email,
                hashed_password,
                user_data.user_type,
                user_data.first_name,
                user_data.last_name,
                user_data.phone
            ))
            
            user = cur.fetchone()
            conn.commit()
            
            # Créer un portefeuille virtuel par défaut
            cur.execute("""
                INSERT INTO portfolios (user_id, name, type, initial_capital, cash_balance)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                user[0],  # user_id
                "Portefeuille Virtuel",
                "virtual",
                10000000,  # 10 millions FCFA
                10000000
            ))
            conn.commit()
            
            # Retourner l'utilisateur créé
            return UserResponse(
                id=user[0],
                email=user[1],
                user_type=user[2],
                first_name=user[3],
                last_name=user[4],
                is_active=user[5],
                is_verified=user[6],
                created_at=user[7]
            )
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'inscription: {str(e)}"
        )
    finally:
        conn.close()

# ==============================================================================
# CONNEXION
# ==============================================================================

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Connexion avec email et mot de passe
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
            # Récupérer l'utilisateur
            cur.execute("""
                SELECT id, email, password_hash, is_active
                FROM users
                WHERE email = %s
            """, (form_data.username,))  # OAuth2 utilise 'username' pour l'email
            
            user = cur.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email ou mot de passe incorrect"
                )
            
            user_id, email, password_hash, is_active = user
            
            # Vérifier le mot de passe
            if not verify_password(form_data.password, password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email ou mot de passe incorrect"
                )
            
            # Vérifier que l'utilisateur est actif
            if not is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Compte désactivé"
                )
            
            # Mettre à jour last_login_at
            cur.execute("""
                UPDATE users
                SET last_login_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (user_id,))
            conn.commit()
            
            # Créer les tokens
            access_token = create_access_token(
                data={"sub": str(user_id), "email": email}
            )
            refresh_token = create_refresh_token(
                data={"sub": str(user_id), "email": email}
            )
            
            return Token(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la connexion: {str(e)}"
        )
    finally:
        conn.close()

# ==============================================================================
# PROFIL UTILISATEUR
# ==============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user = Depends(get_current_user)):
    """
    Récupérer le profil de l'utilisateur connecté
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        user_type=current_user.user_type,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at
    )

# ==============================================================================
# RAFRAÎCHIR TOKEN
# ==============================================================================

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """
    Rafraîchir le token d'accès avec un refresh token
    """
    try:
        from utils.security import decode_token
        token_data = decode_token(refresh_token)
        
        # Créer un nouveau access token
        access_token = create_access_token(
            data={"sub": str(token_data.user_id), "email": token_data.email}
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,  # Garder le même refresh token
            token_type="bearer"
        )
    
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide"
        )
