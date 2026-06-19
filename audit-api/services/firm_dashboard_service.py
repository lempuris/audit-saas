"""Firm-wide oversight dashboard (Phase 4): engagements grouped by status, the
review queue (working papers awaiting reviewer/partner sign-off), overdue
procedures, and the count of uncleared review notes — all across every
engagement. Read-only, so no audit rows. Completed (archived) engagements are
excluded from the work queues; they still count in the status breakdown."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Client,
    Engagement,
    EngagementProcedure,
    ReviewNote,
    User,
    WorkingPaper,
)
from models.audit_programs_models import ProcedureStatus
from models.engagements_models import EngagementStatus
from models.firm_dashboard_models import (
    EngagementStatusBreakdown,
    FirmDashboard,
    OverdueProcedure,
    ReviewQueueItem,
)
from models.review_notes_models import ReviewNoteStatus
from models.working_papers_models import WorkingPaperStatus
from utils.naming import display_name

# Plain strings, not enum members: a set of StrEnum members never matches the
# plain status strings stored on rows (Enum hashes by member name).
REVIEW_QUEUE_STATUSES = {str(WorkingPaperStatus.PREPARED), str(WorkingPaperStatus.REVIEWED)}
OPEN_PROCEDURE_STATUSES = {str(ProcedureStatus.NOT_STARTED), str(ProcedureStatus.IN_PROGRESS)}
UNCLEARED_NOTE_STATUSES = {str(ReviewNoteStatus.OPEN), str(ReviewNoteStatus.RESPONDED)}
ARCHIVED_STATUS = str(EngagementStatus.COMPLETED)


async def firm_dashboard(session: AsyncSession) -> FirmDashboard:
    engagements = list(await session.scalars(select(Engagement)))
    by_id = {engagement.id: engagement for engagement in engagements}
    clients = {client.id: client for client in await session.scalars(select(Client))}
    users = {user.clerk_user_id: user for user in await session.scalars(select(User))}

    def name_of(clerk_user_id: str | None) -> str | None:
        if not clerk_user_id:
            return None
        user = users.get(clerk_user_id)
        return display_name(user.first_name, user.last_name, user.email) if user else None

    def client_name(engagement: Engagement) -> str | None:
        client = clients.get(engagement.client_id)
        return client.name if client else None

    counts = {str(s): 0 for s in EngagementStatus}
    for engagement in engagements:
        counts[engagement.status] = counts.get(engagement.status, 0) + 1
    breakdown = EngagementStatusBreakdown(by_status=counts, total=len(engagements))

    # Completed engagements are archived/read-only — keep them out of the queues.
    active_ids = {
        engagement.id for engagement in engagements if engagement.status != ARCHIVED_STATUS
    }

    review_queue: list[ReviewQueueItem] = []
    for paper in await session.scalars(select(WorkingPaper)):
        engagement = by_id.get(paper.engagement_id)
        if (
            engagement is None
            or paper.engagement_id not in active_ids
            or paper.status not in REVIEW_QUEUE_STATUSES
        ):
            continue
        review_queue.append(
            ReviewQueueItem(
                working_paper_id=paper.id,
                engagement_id=paper.engagement_id,
                client_name=client_name(engagement),
                fiscal_year=engagement.fiscal_year,
                fs_area=paper.fs_area,
                index_ref=paper.index_ref,
                title=paper.title,
                status=paper.status,
                prepared_at=paper.prepared_at,
                prepared_by_name=name_of(paper.prepared_by),
            )
        )
    # Oldest-prepared first (nulls last), then by index for a stable order.
    far_future = datetime.max.replace(tzinfo=UTC)
    review_queue.sort(key=lambda item: (item.prepared_at or far_future, item.index_ref))

    today = datetime.now(UTC).date()
    overdue: list[OverdueProcedure] = []
    for procedure in await session.scalars(select(EngagementProcedure)):
        engagement = by_id.get(procedure.engagement_id)
        if (
            engagement is None
            or procedure.engagement_id not in active_ids
            or procedure.due_date is None
            or procedure.due_date >= today
            or procedure.status not in OPEN_PROCEDURE_STATUSES
        ):
            continue
        overdue.append(
            OverdueProcedure(
                id=procedure.id,
                engagement_id=procedure.engagement_id,
                client_name=client_name(engagement),
                fiscal_year=engagement.fiscal_year,
                fs_area=procedure.fs_area,
                title=procedure.title,
                isa_reference=procedure.isa_reference,
                status=procedure.status,
                due_date=procedure.due_date,
                days_overdue=(today - procedure.due_date).days,
                assignee_name=name_of(procedure.assigned_to),
            )
        )
    overdue.sort(key=lambda item: item.due_date)

    open_review_notes = sum(
        1
        for note in await session.scalars(select(ReviewNote))
        if note.engagement_id in active_ids and note.status in UNCLEARED_NOTE_STATUSES
    )

    return FirmDashboard(
        engagements=breakdown,
        review_queue=review_queue,
        overdue_procedures=overdue,
        open_review_notes=open_review_notes,
    )
