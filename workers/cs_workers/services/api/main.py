from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .settings import settings
from .routers import users, login, projects, simulations

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_PREFIX_STR}/openapi.json",
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(login.router, prefix=settings.API_PREFIX_STR)
app.include_router(users.router, prefix=settings.API_PREFIX_STR)
app.include_router(projects.router, prefix=settings.API_PREFIX_STR)
app.include_router(simulations.router, prefix=settings.API_PREFIX_STR)
