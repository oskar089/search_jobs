from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.auth.router import router as auth_router
from app.portals.router import router as portals_router
from app.profiles.router import router as profiles_router
from app.notifications.router import router as notifications_router

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

# CORS
origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(portals_router, prefix=settings.api_prefix)
app.include_router(profiles_router, prefix=settings.api_prefix)
app.include_router(notifications_router, prefix=settings.api_prefix)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}
