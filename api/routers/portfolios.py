# ==============================================================================
# ROUTER: PORTFOLIOS - Gestion des portefeuilles
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import psycopg2
from uuid import UUID

from api.config import settings
from models.schemas import PortfolioCreate, Portfolio, TransactionCreate, Transaction
from utils.security import get_current_user

router = APIRouter()

@router.get("/", response_model=List[Portfolio])
async def get_my_portfolios(current_user = Depends(get_current_user)):
    """Liste de mes portefeuilles"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_id, name, description, type, initial_capital, current_value, cash_balance, is_active, created_at, updated_at
                FROM portfolios
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (str(current_user.id),))
            
            portfolios = cur.fetchall()
            return [
                Portfolio(
                    id=p[0], user_id=p[1], name=p[2], description=p[3], type=p[4],
                    initial_capital=p[5], current_value=p[6], cash_balance=p[7],
                    is_active=p[8], created_at=p[9], updated_at=p[10]
                )
                for p in portfolios
            ]
    finally:
        conn.close()

@router.post("/", response_model=Portfolio, status_code=status.HTTP_201_CREATED)
async def create_portfolio(data: PortfolioCreate, current_user = Depends(get_current_user)):
    """Créer un nouveau portefeuille"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO portfolios (user_id, name, description, type, initial_capital, current_value, cash_balance)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, name, description, type, initial_capital, current_value, cash_balance, is_active, created_at, updated_at
            """, (str(current_user.id), data.name, data.description, data.type, data.initial_capital, data.initial_capital, data.initial_capital))
            
            portfolio = cur.fetchone()
            conn.commit()
            
            return Portfolio(
                id=portfolio[0], user_id=portfolio[1], name=portfolio[2], description=portfolio[3],
                type=portfolio[4], initial_capital=portfolio[5], current_value=portfolio[6],
                cash_balance=portfolio[7], is_active=portfolio[8], created_at=portfolio[9], updated_at=portfolio[10]
            )
    finally:
        conn.close()

@router.post("/{portfolio_id}/buy", response_model=Transaction)
async def buy_stock(portfolio_id: UUID, transaction: TransactionCreate, current_user = Depends(get_current_user)):
    """Acheter des actions"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            # Vérifier que le portefeuille appartient à l'utilisateur
            cur.execute("SELECT cash_balance FROM portfolios WHERE id = %s AND user_id = %s", (str(portfolio_id), str(current_user.id)))
            portfolio = cur.fetchone()
            
            if not portfolio:
                raise HTTPException(status_code=404, detail="Portefeuille non trouvé")
            
            # Récupérer le company_id et le prix actuel
            cur.execute("""
                SELECT c.id, hd.price
                FROM companies c
                LEFT JOIN LATERAL (
                    SELECT price FROM historical_data WHERE company_id = c.id ORDER BY trade_date DESC LIMIT 1
                ) hd ON true
                WHERE c.symbol = %s
            """, (transaction.symbol.upper(),))
            
            company = cur.fetchone()
            if not company:
                raise HTTPException(status_code=404, detail=f"Société {transaction.symbol} non trouvée")
            
            company_id = company[0]
            price = transaction.price if transaction.price else company[1]
            
            if not price:
                raise HTTPException(status_code=400, detail="Prix non disponible")
            
            # Appeler la fonction PostgreSQL pour créer la transaction
            cur.execute("SELECT create_buy_transaction(%s, %s, %s, %s)", (str(portfolio_id), company_id, transaction.quantity, price))
            transaction_id = cur.fetchone()[0]
            
            # Récupérer la transaction créée
            cur.execute("""
                SELECT id, portfolio_id, company_id, transaction_type, quantity, price, total_amount, fees, net_amount, transaction_date
                FROM transactions WHERE id = %s
            """, (str(transaction_id),))
            
            trans = cur.fetchone()
            conn.commit()
            
            return Transaction(
                id=trans[0], portfolio_id=trans[1], company_id=trans[2], transaction_type=trans[3],
                quantity=trans[4], price=trans[5], total_amount=trans[6], fees=trans[7],
                net_amount=trans[8], transaction_date=trans[9]
            )
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@router.get("/{portfolio_id}/holdings")
async def get_holdings(portfolio_id: UUID, current_user = Depends(get_current_user)):
    """Récupérer les positions du portefeuille"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM v_holdings_enriched WHERE portfolio_id = %s", (str(portfolio_id),))
            holdings = cur.fetchall()
            
            return [
                {
                    "id": h[0], "symbol": h[3], "company_name": h[4], "quantity": h[6],
                    "average_price": float(h[7]), "current_price": float(h[8]) if h[8] else 0,
                    "gain_loss": float(h[10]) if h[10] else 0, "gain_loss_percent": float(h[11]) if h[11] else 0
                }
                for h in holdings
            ]
    finally:
        conn.close()

@router.get("/{portfolio_id}/performance")
async def get_performance(portfolio_id: UUID, current_user = Depends(get_current_user)):
    """Performance du portefeuille"""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME, user=settings.DB_USER,
        password=settings.DB_PASSWORD, host=settings.DB_HOST, port=settings.DB_PORT
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM v_portfolio_performance WHERE portfolio_id = %s", (str(portfolio_id),))
            perf = cur.fetchone()
            
            if not perf:
                raise HTTPException(status_code=404, detail="Portefeuille non trouvé")
            
            return {
                "portfolio_id": perf[0],
                "name": perf[2],
                "initial_capital": float(perf[4]),
                "current_value": float(perf[5]),
                "gain_loss": float(perf[7]),
                "gain_loss_percent": float(perf[8]),
                "holdings_count": perf[9]
            }
    finally:
        conn.close()
