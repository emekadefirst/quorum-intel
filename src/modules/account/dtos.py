from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.common.base_dto import BaseDTO


class AccountObjectDTO(BaseDTO):
    id: UUID
    name: str = Field(..., max_length=255)
    email: EmailStr = Field(..., max_length=255)
    is_active: bool
    last_login: Optional[datetime] = None


class PaginatedAccountDTO(BaseModel):
    page: int
    page_size: int
    total: int
    data: list[AccountObjectDTO]


class CreateAccount(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., max_length=128)


class LoginAccount(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., max_length=128)


class UpdateAccount(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = Field(None, max_length=255)
    is_active: Optional[bool] = None
