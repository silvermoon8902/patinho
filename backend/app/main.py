from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    yield
    # Shutdown
    from app.api.websocket.manager import manager
    await manager.close()


app = FastAPI(
    title="Patinho API",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# CORS middleware
if settings.ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

# Include routers
_routers: list[tuple[str, str, str]] = [
    ("app.api.v1.auth", "router", "/api/v1/auth"),
    ("app.api.v1.users", "router", "/api/v1/users"),
    ("app.api.v1.bets", "router", "/api/v1/bets"),
    ("app.api.v1.payments", "router", "/api/v1/payments"),
    ("app.api.v1.wallet", "router", "/api/v1/wallet"),
    ("app.api.v1.chat", "router", "/api/v1/chat"),
    ("app.api.v1.ranking", "router", "/api/v1/ranking"),
    ("app.api.v1.admin", "router", "/api/v1/admin"),
]

import importlib
import logging

logger = logging.getLogger(__name__)

for module_path, attr_name, prefix in _routers:
    try:
        module = importlib.import_module(module_path)
        router = getattr(module, attr_name)
        app.include_router(router, prefix=prefix)
        logger.info("Loaded router: %s → %s", module_path, prefix)
    except Exception as e:
        logger.error("Failed to load router %s: %s", module_path, e)

# Mount WebSocket router at root level (no prefix)
try:
    from app.api.v1.chat import ws_router as chat_ws_router
    app.include_router(chat_ws_router)
    logger.info("Loaded WebSocket router: /ws/chat")
except Exception as e:
    logger.error("Failed to load WebSocket chat router: %s", e)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
