from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# Imports from your project
from app.core.database import get_db
from app.models.trades import Trade
from app.schemas.trade import TradeResponse  # Your updated schema from Step 1

router = APIRouter()

@router.get("/", response_model=List[TradeResponse])
def list_trades(
    limit: int = 5000, 
    db: Session = Depends(get_db)
):
    """
    Fetch a list of trades from the database.
    """
    try:
        # Do NOT use .load_only() or .with_entities() here.
        # Using .query(Trade).limit(limit).all() ensures all mapped columns 
        # defined in models/trades.py are fetched.
        trades = db.query(Trade).limit(limit).all()
        return trades
    except Exception as e:
        # A good practice to handle query errors gracefully
        raise HTTPException(status_code=500, detail=f"Failed to fetch trades: {str(e)}")