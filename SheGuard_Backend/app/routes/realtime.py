from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from app.services.realtime import realtime_hub
from app.services.security import verify_access_token
from app.database import get_db
from app.models import User
from sqlalchemy.orm import Session

router = APIRouter(tags=['realtime'])


def get_user_from_token(token: str, db: Session) -> User | None:
    '''Verify token and return user if valid.'''
    payload = verify_access_token(token)
    if not payload:
        return None
    user = db.get(User, int(payload['sub']))
    return user


@router.websocket('/ws/live')
async def live_events(websocket: WebSocket, token: str = Query(...)):
    db = next(get_db())
    user = get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001, reason='Invalid token')
        return
    await realtime_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_hub.disconnect(websocket)


@router.websocket('/ws/emergency/{session_id}')
async def emergency_events(websocket: WebSocket, session_id: str, token: str = Query(...)):
    db = next(get_db())
    user = get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001, reason='Invalid token')
        return
    await realtime_hub.connect(websocket, session_id=session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_hub.disconnect(websocket)
