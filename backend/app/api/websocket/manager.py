import asyncio
import json
import logging
from uuid import UUID

from fastapi import WebSocket
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket connection manager with Redis pub/sub.
    Supports multiple uvicorn workers by broadcasting via Redis channels.
    """

    def __init__(self) -> None:
        self._rooms: dict[UUID, set[WebSocket]] = {}
        self._user_map: dict[WebSocket, tuple[UUID, UUID]] = {}  # ws -> (bet_id, user_id)
        self._redis: Redis | None = None
        self._subscriber_tasks: dict[UUID, asyncio.Task] = {}

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    def _channel_name(self, bet_id: UUID) -> str:
        return f"chat:{bet_id}"

    async def connect(
        self, websocket: WebSocket, bet_id: UUID, user_id: UUID
    ) -> None:
        """Accept the WebSocket and add it to the room."""
        await websocket.accept()

        if bet_id not in self._rooms:
            self._rooms[bet_id] = set()

        self._rooms[bet_id].add(websocket)
        self._user_map[websocket] = (bet_id, user_id)

        # Start Redis subscriber for this room if not already running
        if bet_id not in self._subscriber_tasks or self._subscriber_tasks[bet_id].done():
            self._subscriber_tasks[bet_id] = asyncio.create_task(
                self._subscribe(bet_id)
            )

        logger.debug("User %s connected to room %s", user_id, bet_id)

    async def disconnect(self, websocket: WebSocket, bet_id: UUID) -> None:
        """Remove the WebSocket from the room."""
        if bet_id in self._rooms:
            self._rooms[bet_id].discard(websocket)
            if not self._rooms[bet_id]:
                del self._rooms[bet_id]
                # Cancel the subscriber task if no connections remain
                task = self._subscriber_tasks.pop(bet_id, None)
                if task and not task.done():
                    task.cancel()

        self._user_map.pop(websocket, None)
        logger.debug("WebSocket disconnected from room %s", bet_id)

    async def broadcast(self, bet_id: UUID, message: dict) -> None:
        """
        Publish a message to the Redis channel so all workers receive it.
        Each worker's subscriber will then fan out to local WebSocket connections.
        """
        redis = await self._get_redis()
        channel = self._channel_name(bet_id)
        await redis.publish(channel, json.dumps(message, default=str))

    async def send_personal(self, websocket: WebSocket, message: dict) -> None:
        """Send a message to a single WebSocket connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            logger.debug("Failed to send personal message, connection may be closed")

    async def _subscribe(self, bet_id: UUID) -> None:
        """Subscribe to the Redis channel and fan out messages to local connections."""
        redis = await self._get_redis()
        pubsub = redis.pubsub()
        channel = self._channel_name(bet_id)

        try:
            await pubsub.subscribe(channel)
            async for raw_message in pubsub.listen():
                if raw_message["type"] != "message":
                    continue

                data = json.loads(raw_message["data"])
                connections = self._rooms.get(bet_id, set()).copy()

                dead_connections = []
                for ws in connections:
                    try:
                        await ws.send_json(data)
                    except Exception:
                        dead_connections.append(ws)

                # Clean up dead connections
                for ws in dead_connections:
                    await self.disconnect(ws, bet_id)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Error in Redis subscriber for room %s", bet_id)
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass

    async def close(self) -> None:
        """Shut down all subscriber tasks and close Redis connection."""
        for task in self._subscriber_tasks.values():
            if not task.done():
                task.cancel()
        self._subscriber_tasks.clear()

        if self._redis:
            await self._redis.close()
            self._redis = None


# Module-level singleton
manager = ConnectionManager()
