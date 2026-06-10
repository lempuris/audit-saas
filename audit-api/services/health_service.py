from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from models.health_models import HealthResponse


async def get_health(db: AsyncSession) -> HealthResponse:
    # A DB failure propagates to the FastAPI error handler (500), so a 200
    # response always confirms database connectivity.
    result = await db.execute(text("SELECT 1"))
    result.scalar_one()
    return HealthResponse(status="ok", database="ok", environment=get_settings().environment)
