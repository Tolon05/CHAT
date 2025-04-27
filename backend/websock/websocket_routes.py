from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from typing import Dict
from backend.models.models import Message, RoomParticipant, MessageReadStatus
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from backend.auth.token_utils import verify_access_token_for_user_id, verify_access_token_for_user_id_ws
from sqlalchemy import select
from datetime import datetime, timezone

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

@router_ws.websocket("/ws/send_message/{room_id}")
async def send_message_to_room(
    websocket: WebSocket,
    room_id: int,
    db_session: AsyncSession = Depends(get_db)  # Асинхронная сессия с БД
):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            token = data.get("token")
            message = data.get("message", "")

            if not token:
                await websocket.send_json({"event": "error", "message": "Missing token"})
                continue

            if not message:
                await websocket.send_json({"event": "error", "message": "Message cannot be empty"})
                continue

            # Проверка токена и получение sender_id
            try:
                sender_id = await verify_access_token_for_user_id_ws(token)
            except Exception as e:
                await websocket.send_json({"event": "error", "message": f"Invalid token: {str(e)}"})
                continue

            # Сохраняем сообщение в базе
            new_message = Message(
                sender_id=sender_id,
                room_id=room_id,
                content=message,
                timestamp=datetime.now(timezone.utc),
                read=False
            )

            db_session.add(new_message)
            await db_session.commit()

            # Получаем участников комнаты
            async with db_session.begin():
                result = await db_session.execute(select(RoomParticipant).filter_by(room_id=room_id))
                room_participants = result.scalars().all()

            # Отправляем сообщение всем подключённым участникам
            for participant in room_participants:
                user_id = participant.user_id
                ws = connected_users.get(user_id)

                if ws:
                    try:
                        await ws.send_json({
                            "event": "new_message",
                            "sender_id": sender_id,
                            "room_id": room_id,
                            "message": message,
                            "read": False
                        })
                        print(f"Message sent to user {user_id} in room {room_id}: {message}")
                    except Exception as e:
                        print(f"Error sending message to user {user_id} in room {room_id}: {e}")
                else:
                    print(f"User {user_id} is not connected to WebSocket")

            await websocket.send_json({
                "event": "message_sent",
                "status": "success",
                "message": message
            })

    except WebSocketDisconnect:
        print(f"⚫ User disconnected from room {room_id}")
        connected_users.pop(sender_id, None)

    return JSONResponse(status_code=200, content={"message": "Message sent successfully"})

@router_ws.websocket("/ws/read_message/{room_id}/{message_id}")
async def mark_message_as_read(
    websocket: WebSocket,
    room_id: int,
    message_id: int,
    user_id: int = Depends(verify_access_token_for_user_id),  # Получаем идентификатор пользователя из токена
    db_session: AsyncSession = Depends(get_db)  # Сессия с базой данных
):
    await websocket.accept()

    try:
        # Получаем сообщение по ID
        async with db_session.begin():
            result = await db_session.execute(select(Message).filter_by(id=message_id))
            message = result.scalar()

        if not message:
            await websocket.send_json({"event": "error", "message": "Message not found"})
            return

        # Создаем запись в MessageReadStatus для текущего пользователя, если она еще не существует
        async with db_session.begin():
            result = await db_session.execute(select(MessageReadStatus).filter_by(message_id=message_id, user_id=user_id))
            read_status = result.scalar()

        if not read_status:
            # Если записи о прочтении нет, создаем новую
            new_read_status = MessageReadStatus(
                message_id=message_id,
                user_id=user_id,
                read_at=datetime.now(timezone.utc)
            )
            db_session.add(new_read_status)
            await db_session.commit()

        # Проверка, прочитано ли сообщение всеми участниками комнаты
        async with db_session.begin():
            result = await db_session.execute(select(RoomParticipant).filter_by(room_id=room_id))
            room_participants = result.scalars().all()

        # Если все участники прочитали сообщение
        if len(room_participants) == len(message.read_status):
            message.read = True  # Меняем статус сообщения на "прочитано"
            await db_session.commit()

        # Уведомляем всех участников комнаты о прочтении
        await notify_all_users("message_read", user_id)

        await websocket.send_json({
            "event": "message_read_status",
            "message_id": message_id,
            "status": "read"
        })

    except WebSocketDisconnect:
        print(f"⚫ User {user_id} disconnected")

    return JSONResponse(status_code=200, content={"message": "Message marked as read"})




