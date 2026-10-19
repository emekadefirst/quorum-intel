from typing import Any

from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.models import Model


class NotFoundError(Exception): ...


class ConflictError(Exception): ...


class BaseRepository:
    def __init__(self, model: type[Model]):
        self.model = model

    # create action

    async def bulk_create(self, rows: list[dict[str, Any]]) -> None:
        try:
            await self.model.bulk_create([self.model(**row) for row in rows])
        except IntegrityError as error:
            raise ConflictError(f"{self.model.__name__} already exists") from error

    async def create(self, **data: Any) -> Model:
        try:
            return await self.model.create(**data)
        except IntegrityError as error:
            raise ConflictError(f"{self.model.__name__} already exists") from error

    # get action
    async def get(self, *q: Any, **filters: Any) -> Model | None:
        try:
            return await self.model.get(*q, **filters)
        except DoesNotExist:
            return None

    async def get_or_404(self, *q: Any, **filters: Any) -> Model:
        try:
            return await self.model.get(*q, **filters)
        except DoesNotExist:
            raise NotFoundError(f"{self.model.__name__} not found")

    # update action
    async def update(self, obj: Model, **data: Any) -> Model:
        try:
            obj.update_from_dict(data)
            await obj.save()
            return obj
        except IntegrityError as error:
            raise ConflictError(f"{self.model.__name__} already exists") from error

    # delete action
    async def delete(self, id: str) -> None:
        try:
            obj = await self.get_or_404(id=id)
            return await obj.delete()
        except NotFoundError:
            raise NotFoundError(f"{self.model.__name__} not found")

    async def bulk_delete(self, ids: list[str]) -> None:
        try:
            objs = await self.model.filter(id__in=ids).all()
            if not objs:
                raise NotFoundError(f"{self.model.__name__} not found")
            await self.model.filter(id__in=ids).delete()
        except NotFoundError:
            raise NotFoundError(f"{self.model.__name__} not found")
