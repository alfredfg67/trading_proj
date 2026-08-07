from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dal import DatabaseService
from app.schemas.order import OrderCreate, OrderResponse
from app.core.event_queue import publish
from app.dal.base import DatabaseError

router = APIRouter()

@router.post("/", response_model=OrderResponse)
async def create_order(order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    try:
        service = DatabaseService(db)
        new_order = await service.orders.create_order(**order_data.model_dump())
        await publish({"order_id": new_order.id})
        return new_order
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    try:
        service = DatabaseService(db)
        order = await service.orders.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))