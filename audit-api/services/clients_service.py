"""Clients: CRUD with an archive instead of a hard delete, and an
audit-trail row (with before/after snapshots) on every write."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Client
from models.clients_models import ClientCreate, ClientRecord, ClientUpdate
from services import audit_trail_service

ENTITY_TYPE = "client"


def _snapshot(client: Client) -> dict:
    return {
        "name": client.name,
        "industry": client.industry,
        "risk_rating": client.risk_rating,
        "contacts": client.contacts,
        "archived": client.archived,
    }


async def list_clients(
    session: AsyncSession, *, include_archived: bool = False
) -> list[ClientRecord]:
    query = select(Client).order_by(Client.name)
    if not include_archived:
        query = query.where(Client.archived.is_(False))
    rows = await session.scalars(query)
    return [ClientRecord.model_validate(row) for row in rows]


async def _get(session: AsyncSession, client_id: uuid.UUID) -> Client:
    client = (await session.scalars(select(Client).where(Client.id == client_id))).first()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


async def get_client(session: AsyncSession, client_id: uuid.UUID) -> ClientRecord:
    return ClientRecord.model_validate(await _get(session, client_id))


async def create_client(
    session: AsyncSession, *, actor: str, payload: ClientCreate
) -> ClientRecord:
    client = Client(
        id=uuid.uuid4(),
        name=payload.name,
        industry=payload.industry,
        risk_rating=payload.risk_rating,
        contacts=[contact.model_dump() for contact in payload.contacts],
        archived=False,
    )
    session.add(client)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(client.id),
        after=_snapshot(client),
    )
    await session.commit()
    await session.refresh(client)
    return ClientRecord.model_validate(client)


async def update_client(
    session: AsyncSession, *, actor: str, client_id: uuid.UUID, payload: ClientUpdate
) -> ClientRecord:
    client = await _get(session, client_id)
    before = _snapshot(client)

    changes = payload.model_dump(exclude_unset=True)
    if "contacts" in changes and changes["contacts"] is not None:
        changes["contacts"] = [contact.model_dump() for contact in payload.contacts or []]
    for field, value in changes.items():
        setattr(client, field, value)

    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(client_id),
        before=before,
        after=_snapshot(client),
    )
    await session.commit()
    await session.refresh(client)
    return ClientRecord.model_validate(client)


async def archive_client(
    session: AsyncSession, *, actor: str, client_id: uuid.UUID
) -> ClientRecord:
    client = await _get(session, client_id)
    before = _snapshot(client)
    client.archived = True
    audit_trail_service.record(
        session,
        actor=actor,
        action="delete",
        entity_type=ENTITY_TYPE,
        entity_id=str(client_id),
        before=before,
        after=_snapshot(client),
    )
    await session.commit()
    await session.refresh(client)
    return ClientRecord.model_validate(client)
