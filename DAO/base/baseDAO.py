from typing import Any, Type, TypeVar, Tuple, List, Generic, Coroutine, Optional
from sqlalchemy import select, delete as sql_delete, update as sql_update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import MultipleResultsFound
ModelType = TypeVar("ModelType")

class BaseDAO(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model
        self._primary_keys = inspect(model).primary_key

    def _get_primary_key_names(self) -> Tuple[str, ...]:
        return tuple(col.name for col in self._primary_keys)

    def _build_conditions(self, *primary_key_values: Any, **filters: Any):
        conditions = []
        if primary_key_values:
            if len(primary_key_values) != len(self._primary_keys):
                raise ValueError(
                    f"提供的主键值数量（{len(primary_key_values)}）"
                    f"与模型 {self.model.__name__} 的主键数量（{len(self._primary_keys)}）不匹配"
                )
            for col, val in zip(self._primary_keys, primary_key_values):
                conditions.append(col == val)
        for field_name, value in filters.items():
            if not hasattr(self.model, field_name):
                raise AttributeError(f"模型 {self.model.__name__} 没有字段 '{field_name}'")
            column = getattr(self.model, field_name)
            conditions.append(column == value)
        if not conditions:
            raise ValueError("未提供任何查询条件")
        return conditions

    async def get(
            self,
            db: AsyncSession,
            *primary_key_values: Any,
            **filters: Any
    ) -> Optional[ModelType]:
        try:
            conditions = self._build_conditions(*primary_key_values, **filters)
            stmt = select(self.model).where(*conditions).limit(2)
            result = await db.execute(stmt)
            return result.scalars().one_or_none()
        except MultipleResultsFound:
            return None
        # 不捕获其他 Exception，让 bug 暴露出来（或按需处理）


    async def insert(self, db: AsyncSession, obj: ModelType) -> Optional[ModelType]:
        """插入对象，成功返回实例（含数据库生成的字段如ID），失败返回 None"""
        try:
            if not isinstance(obj, self.model):
                return None
            db.add(obj)
            await db.commit()
            await db.refresh(obj)  # 确保获取自增ID等
            return obj
        except Exception:
            await db.rollback()
            return None


    async def update(self, db: AsyncSession, obj: ModelType) -> Optional[ModelType]:
        """更新对象，成功返回更新后的实例，失败返回 None"""
        try:
            if not isinstance(obj, self.model):
                return None
            # 确保主键存在
            pk_names = self._get_primary_key_names()
            for pk in pk_names:
                if getattr(obj, pk) is None:
                    return None
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
            return obj
        except Exception:
            await db.rollback()
            return None


    async def delete(
            self,
            db: AsyncSession,
            *primary_key_values: Any,
            **filters: Any
    ) -> Optional[ModelType]:
        """删除单条记录，成功返回被删除的对象，失败返回 None"""
        try:
            # 先查询
            conditions = self._build_conditions(*primary_key_values, **filters)
            stmt = select(self.model).where(*conditions).limit(1)
            result = await db.execute(stmt)
            obj = result.scalar_one_or_none()
            if obj is None:
                return None
            # 再删除
            await db.delete(obj)
            await db.commit()
            return obj
        except Exception:
            await db.rollback()
            return None


    async def delete_many(
            self,
            db: AsyncSession,
            *primary_key_values: Any,
            **filters: Any
    ) -> Optional[List[ModelType]]:
        """批量删除，成功返回被删除的对象列表，失败返回 None"""
        try:
            # 先查询所有匹配项
            conditions = self._build_conditions(*primary_key_values, **filters)
            stmt = select(self.model).where(*conditions)
            result = await db.execute(stmt)
            objs = result.scalars().all()
            if not objs:
                return []  # 没有匹配项，但操作成功 → 返回空列表（非 None）

            # 删除所有
            for obj in objs:
                await db.delete(obj)
            await db.commit()
            return list(objs)
        except Exception:
            await db.rollback()
            return None
