from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from middleware.auth import ClerkAuthMiddleware
from routers import (
    audit_programs_router,
    audit_trail_router,
    auth_router,
    clerk_webhook_router,
    clients_router,
    engagements_router,
    health_router,
    materiality_router,
    risks_router,
    trial_balance_router,
    users_router,
)

settings = get_settings()

app = FastAPI(title=settings.app_name)

# Starlette runs middleware in reverse add order: CORS (added last) is
# outermost so it answers preflight requests before auth sees them.
app.add_middleware(ClerkAuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router.router)
app.include_router(auth_router.router)
app.include_router(clerk_webhook_router.router)
app.include_router(audit_trail_router.router)
app.include_router(users_router.router)
app.include_router(clients_router.router)
app.include_router(engagements_router.router)
app.include_router(trial_balance_router.router)
app.include_router(materiality_router.router)
app.include_router(risks_router.router)
app.include_router(audit_programs_router.templates_router)
app.include_router(audit_programs_router.router)
