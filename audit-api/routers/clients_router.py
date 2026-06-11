import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.clients_models import ClientCreate, ClientRecord, ClientUpdate
from services import clients_service

router = APIRouter(prefix="/api/clients", tags=["clients"])

# Reads: any staff role. Writes: Manager and above. Archive: Partner/Admin.
Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
Writer = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
Archiver = Annotated[AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER))]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[ClientRecord])
async def list_clients(_user: Reader, db: Db, include_archived: bool = False) -> list[ClientRecord]:
    return await clients_service.list_clients(db, include_archived=include_archived)


@router.get("/{client_id}", response_model=ClientRecord)
async def get_client(client_id: uuid.UUID, _user: Reader, db: Db) -> ClientRecord:
    return await clients_service.get_client(db, client_id)


@router.post("", response_model=ClientRecord, status_code=201)
async def create_client(body: ClientCreate, user: Writer, db: Db) -> ClientRecord:
    return await clients_service.create_client(db, actor=user.user_id, payload=body)


@router.patch("/{client_id}", response_model=ClientRecord)
async def update_client(
    client_id: uuid.UUID, body: ClientUpdate, user: Writer, db: Db
) -> ClientRecord:
    return await clients_service.update_client(
        db, actor=user.user_id, client_id=client_id, payload=body
    )


@router.delete("/{client_id}", response_model=ClientRecord)
async def archive_client(client_id: uuid.UUID, user: Archiver, db: Db) -> ClientRecord:
    return await clients_service.archive_client(db, actor=user.user_id, client_id=client_id)
