import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.auth_models import Role


class UserRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clerk_user_id: str
    email: str | None
    first_name: str | None
    last_name: str | None
    role: str | None
    is_active: bool
    created_at: datetime


class InviteRequest(BaseModel):
    email: str
    role: Role


class RoleUpdateRequest(BaseModel):
    role: Role
