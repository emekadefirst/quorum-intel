import uuid

from tortoise import fields
from tortoise.models import Model


class BaseModel(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4, editable=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(null=True)

    class Meta(Model.Meta):
        abstract = True
