# ==============================================================================
# ROUTER: WATCHLISTS - Listes de surveillance
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import psycopg2
from uuid import UUID

from api.config import settings
from models.schemas import WatchlistCreate, Watchlist, WatchlistItemAdd
from utils.security import get_current_user

router = APIRouter()

@router.get("/", response_model=List[Watchlist])
async def get_watchlists(current_user = Depends(get_current_user)):
    """Liste de mes watchlists"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_id, name, description, is_default, created_at
                FROM watchlists
                WHERE user_id = %s
                ORDER BY is_default DESC, created_at DESC
            """, (str(current_user.id),))
            
            watchlists = cur.fetchall()
            return [
                Watchlist(
                    id=w[0], user_id=w[1], name=w[2], description=w[3],
                    is_default=w[4], created_at=w[5]
                )
                for w in watchlists
            ]
    finally:
        conn.close()

@router.post("/", response_model=Watchlist, status_code=status.HTTP_201_CREATED)
async def create_watchlist(data: WatchlistCreate, current_user = Depends(get_current_user)):
    """Créer une watchlist"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO watchlists (user_id, name, description)
                VALUES (%s, %s, %s)
                RETURNING id, user_id, name, description, is_default, created_at
            """, (str(current_user.id), data.name, data.description))
            
            watchlist = cur.fetchone()
            conn.commit()
            
            return Watchlist(
                id=watchlist[0], user_id=watchlist[1], name=watchlist[2],
                description=watchlist[3], is_default=watchlist[4], created_at=watchlist[5]
            )
    finally:
        conn.close()

@router.post("/{watchlist_id}/add")
async def add_to_watchlist(watchlist_id: UUID, item: WatchlistItemAdd, current_user = Depends(get_current_user)):
    """Ajouter une société à la watchlist"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            # Vérifier que la watchlist appartient à l'utilisateur
            cur.execute("SELECT id FROM watchlists WHERE id = %s AND user_id = %s", (str(watchlist_id), str(current_user.id)))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Watchlist non trouvée")
            
            # Récupérer le company_id
            cur.execute("SELECT id FROM companies WHERE symbol = %s", (item.symbol.upper(),))
            company = cur.fetchone()
            
            if not company:
                raise HTTPException(status_code=404, detail=f"Société {item.symbol} non trouvée")
            
            # Ajouter à la watchlist
            cur.execute("""
                INSERT INTO watchlist_items (watchlist_id, company_id, notes)
                VALUES (%s, %s, %s)
                ON CONFLICT (watchlist_id, company_id) DO NOTHING
            """, (str(watchlist_id), company[0], item.notes))
            
            conn.commit()
            return {"message": f"{item.symbol} ajouté à la watchlist"}
    finally:
        conn.close()

@router.delete("/{watchlist_id}/remove/{symbol}")
async def remove_from_watchlist(watchlist_id: UUID, symbol: str, current_user = Depends(get_current_user)):
    """Retirer une société de la watchlist"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM watchlist_items
                WHERE watchlist_id = %s
                AND company_id = (SELECT id FROM companies WHERE symbol = %s)
                AND watchlist_id IN (SELECT id FROM watchlists WHERE user_id = %s)
            """, (str(watchlist_id), symbol.upper(), str(current_user.id)))
            
            conn.commit()
            return {"message": f"{symbol} retiré de la watchlist"}
    finally:
        conn.close()

@router.get("/{watchlist_id}/items")
async def get_watchlist_items(watchlist_id: UUID, current_user = Depends(get_current_user)):
    """Récupérer les sociétés d'une watchlist"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM v_watchlists_detailed WHERE watchlist_id = %s AND user_id = %s", (str(watchlist_id), str(current_user.id)))
            items = cur.fetchall()
            
            return [
                {
                    "symbol": i[5], "name": i[6], "current_price": float(i[8]) if i[8] else 0,
                    "mm_decision": i[9], "rsi_decision": i[10], "notes": i[11]
                }
                for i in items if i[5]  # Filtrer les None
            ]
    finally:
        conn.close()
