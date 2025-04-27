from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict

router_ws = APIRouter()

connected_users: Dict[int, WebSocket] = {}

@router_ws.websocket("/ws/online/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    connected_users[user_id] = websocket

    # 🔥 Отправка новому пользователю текущего списка онлайн
    await websocket.send_json({
        "event": "online_users_list",
        "users": list(connected_users.keys())
    })

    # 🔥 Уведомляем всех остальных о новом онлайн-пользователе
    await notify_all_users("user_online", user_id)
    print(f"🔵 User {user_id} is online. Total connected: {len(connected_users)}")

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        connected_users.pop(user_id, None)
        await notify_all_users("user_offline", user_id)
        print(f"⚫ User {user_id} went offline. Total connected: {len(connected_users)}")

async def notify_all_users(event: str, user_id: int):
    for uid, ws in connected_users.items():
        if uid != user_id:
            try:
                print("send status")
                await ws.send_json({
                    "event": event,
                    "user_id": user_id
                })
            except:
                pass

# @router_ws.get("/online_users")
# async def get_online_users():
#     return JSONResponse(content={"users": list(connected_users.keys())})
