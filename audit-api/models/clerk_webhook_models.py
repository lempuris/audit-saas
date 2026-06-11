from typing import Any

from pydantic import BaseModel, ConfigDict


class ClerkEmailAddress(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    email_address: str


class ClerkUserData(BaseModel):
    """The `data` object of user.created / user.updated events (and the
    id-only shape of user.deleted)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    first_name: str | None = None
    last_name: str | None = None
    email_addresses: list[ClerkEmailAddress] = []
    primary_email_address_id: str | None = None
    public_metadata: dict[str, Any] = {}

    @property
    def primary_email(self) -> str | None:
        for address in self.email_addresses:
            if address.id == self.primary_email_address_id:
                return address.email_address
        return self.email_addresses[0].email_address if self.email_addresses else None

    @property
    def role(self) -> str | None:
        role = self.public_metadata.get("role")
        return role if isinstance(role, str) and role else None


class ClerkEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    data: dict[str, Any]
