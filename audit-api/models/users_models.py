import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from models.auth_models import Role
from utils.naming import display_name


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

    @computed_field
    @property
    def display_name(self) -> str:
        # Never blank: full name → email local-part → Clerk id.
        return display_name(self.first_name, self.last_name, self.email) or self.clerk_user_id


class InviteRequest(BaseModel):
    email: str
    role: Role


class RoleUpdateRequest(BaseModel):
    role: Role
