import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.websocket.manager import manager
from app.database import async_session_maker, get_db
from app.models.bet import Bet
from app.models.chat_message import ChatMessage
from app.models.participation import Participation
from app.models.user import User
from app.services import league_service
from app.services.auth_service import get_current_active_user
from app.utils.security import decode_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

# Separate router for WebSocket (mounted at root level in main.py)
ws_router = APIRouter()


async def _authenticate_ws_user(token: str, db: AsyncSession) -> User | None:
    """Authenticate a WebSocket connection via query param token."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = UUID(payload.get("sub", ""))
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None


@ws_router.websocket("/ws/chat/{bet_id}")
async def chat_websocket(websocket: WebSocket, bet_id: UUID, token: str = Query(...)):
    """
    WebSocket endpoint for bet chat.
    Auth via query param ?token=<jwt>.
    Messages are saved to DB and broadcast to all participants in the room.
    """
    async with async_session_maker() as db:
        # Authenticate user
        user = await _authenticate_ws_user(token, db)
        if not user:
            await websocket.close(code=4001, reason="Authentication failed")
            return

        # Check bet exists
        bet = await db.get(Bet, bet_id)
        if not bet:
            await websocket.close(code=4004, reason="Bet not found")
            return

        # League-scoped bets: non-members cannot listen in on the chat.
        # Creator always allowed (they may need to moderate).
        try:
            await league_service.require_bet_access(db, bet, user.id)
        except HTTPException:
            await websocket.close(code=4004, reason="Bet not found")
            return

        # Check chat is still open
        now = datetime.now(timezone.utc)
        if bet.chat_closes_at and bet.chat_closes_at <= now:
            await websocket.close(code=4003, reason="Chat is closed")
            return

    # Connect to room
    await manager.connect(websocket, bet_id, user.id)

    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "").strip()

            if not content or len(content) > 1000:
                await manager.send_personal(
                    websocket, {"error": "Message must be 1-1000 characters"}
                )
                continue

            # Save message to DB in a fresh session
            async with async_session_maker() as db:
                try:
                    # Re-check chat is still open
                    bet = await db.get(Bet, bet_id)
                    if bet and bet.chat_closes_at and bet.chat_closes_at <= datetime.now(timezone.utc):
                        await manager.send_personal(
                            websocket, {"error": "Chat is closed"}
                        )
                        break

                    message = ChatMessage(
                        bet_id=bet_id,
                        user_id=user.id,
                        content=content,
                    )
                    db.add(message)
                    await db.commit()

                    # Broadcast to all connections in this room
                    await manager.broadcast(bet_id, {
                        "type": "message",
                        "id": str(message.id),
                        "user_id": str(user.id),
                        "username": user.username,
                        "content": content,
                        "created_at": message.created_at.isoformat() if message.created_at else None,
                    })
                except Exception:
                    await db.rollback()
                    logger.exception("Error saving chat message")
                    await manager.send_personal(
                        websocket, {"error": "Failed to send message"}
                    )
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error for user %s in bet %s", user.id, bet_id)
    finally:
        await manager.disconnect(websocket, bet_id)


@router.get("/{bet_id}/messages")
async def list_messages(
    bet_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List chat messages for a bet, paginated."""
    from fastapi import status

    bet = await db.get(Bet, bet_id)
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    await league_service.require_bet_access(db, bet, user.id)

    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.bet_id == bet_id,
            ChatMessage.deleted_at.is_(None),
        )
        .order_by(ChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()

    # Load usernames
    user_ids = {m.user_id for m in messages}
    user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_map = {u.id: u.username for u in user_result.scalars().all()}

    return [
        {
            "id": m.id,
            "user_id": m.user_id,
            "username": users_map.get(m.user_id, "unknown"),
            "content": m.content,
            "is_system": m.is_system,
            "created_at": m.created_at,
        }
        for m in messages
    ]
