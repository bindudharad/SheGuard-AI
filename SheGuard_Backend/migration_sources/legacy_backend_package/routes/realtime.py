from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.realtime import realtime_hub


router = APIRouter(tags=["realtime"])


@router.websocket("/ws/live")
async def live_events(websocket: WebSocket):
    await realtime_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_hub.disconnect(websocket)

