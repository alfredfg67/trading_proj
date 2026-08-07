from typing import TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)

class DatabaseError(Exception):
    pass

class BaseRepository:
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def create(self, **kwargs) -> ModelType:
        try:
            instance = self.model(**kwargs)
            self.db.add(instance)
            await self.db.commit()
            await self.db.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to create {self.model.__name__}: {e}")

    async def bulk_create(self, instances: List[Dict[str, Any]]) -> List[ModelType]:
        try:
            models = [self.model(**data) for data in instances]
            self.db.add_all(models)
            await self.db.commit()
            for model in models:
                await self.db.refresh(model)
            return models
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to bulk create {self.model.__name__}: {e}")

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        try:
            result = await self.db.execute(select(self.model).where(self.model.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get {self.model.__name__} by id {id}: {e}")

    async def get_all(self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> List[ModelType]:
        try:
            query = select(self.model)
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.where(getattr(self.model, key) == value)
            query = query.offset(skip).limit(limit)
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get {self.model.__name__} list: {e}")

    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        try:
            await self.db.execute(update(self.model).where(self.model.id == id).values(**kwargs))
            await self.db.commit()
            return await self.get_by_id(id)
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to update {self.model.__name__} id {id}: {e}")

    async def delete(self, id: int) -> bool:
        try:
            result = await self.db.execute(delete(self.model).where(self.model.id == id))
            await self.db.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to delete {self.model.__name__} id {id}: {e}")

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        try:
            query = select(func.count()).select_from(self.model)
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.where(getattr(self.model, key) == value)
            result = await self.db.execute(query)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to count {self.model.__name__}: {e}")

    async def exists(self, **kwargs) -> bool:
        try:
            query = select(func.count()).select_from(self.model)
            for key, value in kwargs.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            result = await self.db.execute(query)
            return (result.scalar() or 0) > 0
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to check existence for {self.model.__name__}: {e}")