import uuid
from tortoise import Model, fields

class BaseModel(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4, editable=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(null=True)

    def __str__(self):
        return getattr(self, "email", str(self.id))

    class Meta:
        abstract = True

