from tortoise import fields

from src.common.base_model import BaseModel


class Account(BaseModel):
    name = fields.CharField(max_length=255, unique=True)
    email = fields.CharField(max_length=255, unique=True)
    password = fields.CharField(max_length=255)
    last_login = fields.DatetimeField(null=True)
    is_active = fields.BooleanField(default=False)

    class Meta:
        table = "accounts"
        indexes = ["id", "name", "email"]

    def __str__(self) -> str:
        return self.name
