import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .bootstrap import ensure_event_config, ensure_jukebox_runtime, ensure_operator
from .config import get_settings
from .database import SessionLocal
from .middleware import FrameAncestorsMiddleware
from .routers import auth, auth_google, health, participant, queue, state, tokens, votes, youtube


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
        ensure_jukebox_runtime(db)
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
            # Scoped to the headers the SPA actually sends; `*` is disallowed
            # alongside credentials (010-hardening-and-polish, FR-007).
            allow_headers=["Content-Type"],
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
    app.include_router(auth_google.router)
    app.include_router(tokens.router)
    app.include_router(state.router)
    app.include_router(queue.router)
    app.include_router(participant.router)
    app.include_router(votes.router)
    app.include_router(youtube.router)

    return app


app = create_app()
