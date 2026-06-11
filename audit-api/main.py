from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from middleware.auth import ClerkAuthMiddleware
from routers import auth_router, health_router

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
