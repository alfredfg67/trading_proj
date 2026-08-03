from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.orders import Order
from app.schemas.order import OrderCreate, OrderResponse
from app.core.event_queue import publish

router = APIRouter()

@router.post("/", response_model=OrderResponse)
async def create_order(order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    new_order = Order(**order_data.model_dump())
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)
    await publish({"order_id": new_order.id})
    return new_order

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order