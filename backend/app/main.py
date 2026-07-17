import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .bootstrap import ensure_event_config, ensure_operator
from .config import get_settings
from .database import SessionLocal
from .middleware import FrameAncestorsMiddleware
from .routers import auth, health, tokens


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = SessionLocal()
    try:
        ensure_operator(
            db,
            username=settings.operator_username,
            password=settings.operator_password,
        )
        ensure_event_config(db)
    except ValueError as exc:
        logger.error("Bootstrap failed: %s", exc)
        raise
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="jukebox-backend", version="0.1.0", lifespan=lifespan)

    origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="jukebox_session",
        same_site="lax",
        https_only=settings.cookie_secure,
        max_age=60 * 60 * 24 * 7,
    )

    app.add_middleware(FrameAncestorsMiddleware, value=settings.frame_ancestors)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(tokens.router)

    return app


app = create_app()
