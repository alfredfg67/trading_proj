from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dal import DatabaseService
from app.schemas.order import OrderCreate, OrderResponse
from app.core.event_queue import publish
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.dal.base import DatabaseError

router = APIRouter()

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new order. The order will be linked to the user's default account (account_id=1 for now).
    In a future phase, we'll allow selecting which account to use.
    """
    service = DatabaseService(db)
    try:
        new_order = await service.orders.create_order(**order_data.model_dump())
        # Note: The order itself doesn't have a broker_account_id, only the trade does.
        # The order processor will create the trade and assign broker_account_id.
        # For now, we keep the hardcoded value in order_processor.
        await publish({"order_id": new_order.id})
        return new_order
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve an order by ID.
    """
    service = DatabaseService(db)
    try:
        order = await service.orders.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        # Optional: verify that the order belongs to the user (via trades)
        # For now, we assume all orders are visible to all users (but we'll improve later)
        return order
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))