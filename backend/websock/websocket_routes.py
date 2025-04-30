from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from typing import Dict
from backend.models.models import Message, RoomParticipant, MessageReadStatus, ChatRoom as Room
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from backend.auth.token_utils import verify_access_token_for_user_id, verify_access_token_for_user_id_ws
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

router_ws = APIRouter()

connected_users: Dict[int, WebSocket] = {}

@router_ws.websocket("/ws/online/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, db_session: AsyncSession = Depends(get_db)):
    await websocket.accept()
    connected_users[user_id] = websocket

    # Получаем список личных комнат пользователя
    result = await db_session.execute(
        select(RoomParticipant.room_id)
        .join(Room, RoomParticipant.room_id == Room.id)
        .filter(RoomParticipant.user_id == user_id, Room.type == 'personal')
    )
    personal_room_ids = result.scalars().all()

    # Отправляем список онлайн-пользователей только для личных комнат
    online_users = []
    for uid in connected_users.keys():
        result = await db_session.execute(
            select(RoomParticipant).filter_by(user_id=uid)
        )
        user_rooms = result.scalars().all()
        if any(room.room_id in personal_room_ids for room in user_rooms):
            online_users.append(uid)

    await websocket.send_json({
        "event": "online_users_list",
        "users": online_users
    })

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

@router_ws.websocket("/ws/chat/{room_id}")
async def chat_endpoint(
    websocket: WebSocket,
    room_id: int,
    db_session: AsyncSession = Depends(get_db)
):
    await websocket.accept()
    user_id = None

    try:
        # Получаем токен из первого сообщения
        data = await websocket.receive_json()
        token = data.get("token")
        if not token:
            await websocket.send_json({"event": "error", "message": "Missing token"})
            await websocket.close()
            return

        # Проверка токена и получение user_id
        try:
            user_id = await verify_access_token_for_user_id_ws(token)
        except Exception as e:
            await websocket.send_json({"event": "error", "message": f"Invalid token: {str(e)}"})
            await websocket.close()
            return

        # Проверяем, является ли пользователь участником комнаты
        result = await db_session.execute(
            select(RoomParticipant).filter_by(room_id=room_id, user_id=user_id)
        )
        participant = result.scalar_one_or_none()
        if not participant:
            await websocket.send_json({"event": "error", "message": "User not in this room"})
            await websocket.close()
            return

        # Загружаем историю сообщений с предзагрузкой статусов прочтения
        result = await db_session.execute(
            select(Message)
            .filter_by(room_id=room_id)
            .options(
                selectinload(Message.read_status),
                selectinload(Message.sender)
            )
            .order_by(Message.timestamp.asc())
        )
        messages = result.scalars().all()

        # Формируем список сообщений для отправки
        message_history = []
        for msg in messages:
            read_by = [status.user_id for status in msg.read_status]
            avatar_data = base64.b64encode(msg.sender.avatar_data).decode('utf-8') if msg.sender.avatar_data else None
            image_data = base64.b64encode(msg.image_data).decode('utf-8') if msg.image_data else None
            message_history.append({
                "sender_id": msg.sender_id,
                "sender_username": msg.sender.username,
                "avatar_data": avatar_data,
                "content": msg.content,
                "image_data": image_data,
                "timestamp": msg.timestamp.isoformat(),
                "message_id": msg.id,
                "read_by": read_by
            })

        # Отправляем историю сообщений
        await websocket.send_json({
            "event": "message_history",
            "messages": message_history
        })

        # Добавляем пользователя в connected_users, если его там нет
        connected_users[user_id] = websocket

        # Обрабатываем новые события
        try:
            while True:
                await websocket.receive_text()  # Держим соединение открытым
        except WebSocketDisconnect:
            if user_id in connected_users:
                connected_users.pop(user_id, None)
                await notify_all_users("user_offline", user_id)
            print(f"⚫ User {user_id} disconnected from chat in room {room_id}")

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        await websocket.send_json({"event": "error", "message": "Internal server error"})
        await websocket.close()

import base64

@router_ws.websocket("/ws/send_message/{room_id}")
async def send_message_to_room(
    websocket: WebSocket,
    room_id: int,
    db_session: AsyncSession = Depends(get_db)
):
    await websocket.accept()
    sender_id = None

    try:
        while True:
            data = await websocket.receive_json()

            token = data.get("token")
            message = data.get("message", "")  # Может быть пустой строкой
            image_data = data.get("image_data")  # Данные изображения в формате base64

            if not token:
                await websocket.send_json({"event": "error", "message": "Missing token"})
                continue

            try:
                sender_id = await verify_access_token_for_user_id_ws(token)
            except Exception as e:
                await websocket.send_json({"event": "error", "message": f"Invalid token: {str(e)}"})
                continue

            # Проверяем, является ли пользователь участником комнаты
            result = await db_session.execute(
                select(RoomParticipant).filter_by(room_id=room_id, user_id=sender_id)
            )
            participant = result.scalar_one_or_none()
            if not participant:
                await websocket.send_json({"event": "error", "message": "User not in this room"})
                continue

            # Извлекаем данные пользователя
            result = await db_session.execute(
                select(User.id, User.username, User.avatar_data).filter_by(id=sender_id)
            )
            sender_data = result.first()

            if not sender_data:
                await websocket.send_json({"event": "error", "message": "Sender not found"})
                continue

            sender_id, sender_username, sender_avatar_data = sender_data

            # Декодируем изображение из base64, если оно есть
            image_binary = None
            if image_data:
                try:
                    # Удаляем префикс "data:image/..." из base64-строки, если он есть
                    image_binary = base64.b64decode(image_data.split(",")[1] if "," in image_data else image_data)
                except Exception as e:
                    await websocket.send_json({"event": "error", "message": f"Invalid image data: {str(e)}"})
                    continue

            # Сохраняем сообщение
            new_message = Message(
                sender_id=sender_id,
                room_id=room_id,
                content=message,
                image_data=image_binary,
                timestamp=datetime.now(timezone.utc)
            )
            db_session.add(new_message)
            await db_session.commit()
            await db_session.refresh(new_message)

            message_id = new_message.id
            message_timestamp = new_message.timestamp.isoformat()

            # Отмечаем сообщение как прочитанное отправителем
            read_status = MessageReadStatus(
                message_id=message_id,
                user_id=sender_id,
                read_at=datetime.now(timezone.utc)
            )
            db_session.add(read_status)
            await db_session.commit()

            # Получаем список участников комнаты
            result = await db_session.execute(
                select(RoomParticipant.user_id).filter_by(room_id=room_id)
            )
            participant_ids = result.scalars().all()
            other_participant_ids = [uid for uid in participant_ids if uid != sender_id]

            # Кодируем аватар и изображение для отправки
            avatar_data = base64.b64encode(sender_avatar_data).decode('utf-8') if sender_avatar_data else None
            image_data_response = base64.b64encode(image_binary).decode('utf-8') if image_binary else None

            # Формируем данные сообщения
            message_data = {
                "event": "new_message",
                "status": "success",
                "content": message,
                "image_data": image_data_response,
                "message_id": message_id,
                "timestamp": message_timestamp,
                "sender_username": sender_username,
                "avatar_data": avatar_data,
                "sender_id": sender_id
            }

            # Отправляем сообщение участникам комнаты
            for user_id in other_participant_ids:
                ws = connected_users.get(user_id)
                if ws:
                    try:
                        await ws.send_json(message_data)
                        print(f"Message sent to user {user_id} in room {room_id}: {message}")
                    except Exception as e:
                        print(f"Error sending message to user {user_id} in room {room_id}: {e}")
                else:
                    print(f"User {user_id} is not connected to WebSocket")

            # Подтверждаем отправителю
            await websocket.send_json({
                "event": "message_sent",
                "status": "success",
                "message": message,
                "image_data": image_data_response,
                "message_id": message_id,
                "timestamp": message_timestamp,
                "sender_username": sender_username,
                "avatar_data": avatar_data
            })

    except WebSocketDisconnect:
        if sender_id:
            connected_users.pop(sender_id, None)
        print(f"⚫ User disconnected from room {room_id}")

    return JSONResponse(status_code=200, content={"message": "Message sent successfully"})

@router_ws.websocket("/ws/read_message/{room_id}/{message_id}")
async def mark_message_as_read(
    websocket: WebSocket,
    room_id: int,
    message_id: int,
    user_id: int = Depends(verify_access_token_for_user_id),
    db_session: AsyncSession = Depends(get_db)
):
    await websocket.accept()

    try:
        result = await db_session.execute(select(Message).filter_by(id=message_id))
        message = result.scalar_one_or_none()

        if not message:
            await websocket.send_json({"event": "error", "message": "Message not found"})
            return

        result = await db_session.execute(
            select(MessageReadStatus).filter_by(message_id=message_id, user_id=user_id)
        )
        read_status = result.scalar_one_or_none()

        if not read_status:
            new_read_status = MessageReadStatus(
                message_id=message_id,
                user_id=user_id,
                read_at=datetime.now(timezone.utc)
            )
            db_session.add(new_read_status)
            await db_session.commit()

        result = await db_session.execute(select(RoomParticipant).filter_by(room_id=room_id))
        room_participants = result.scalars().all()

        if len(room_participants) == len(message.read_status):
            message.read = True
            await db_session.commit()

        await notify_all_users("message_read", user_id)

        await websocket.send_json({
            "event": "message_read_status",
            "message_id": message_id,
            "status": "read"
        })

    except WebSocketDisconnect:
        print(f"⚫ User {user_id} disconnected")

    return JSONResponse(status_code=200, content={"message": "Message marked as read"})






from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from typing import Dict
from backend.models.models import Message, RoomParticipant, MessageReadStatus, ChatRoom as Room, User
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from backend.auth.token_utils import verify_access_token_for_user_id_ws
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
import base64

@router_ws.websocket("/ws/delete_message/{room_id}/{message_id}")
async def delete_message(
    websocket: WebSocket,
    room_id: int,
    message_id: int,
    db_session: AsyncSession = Depends(get_db)
):
    await websocket.accept()
    user_id = None

    try:
        # Получаем токен
        data = await websocket.receive_json()
        token = data.get("token")

        if not token:
            await websocket.send_json({"event": "error", "message": "Missing token"})
            await websocket.close()
            return

        # Проверка токена
        try:
            user_id = await verify_access_token_for_user_id_ws(token)
        except Exception as e:
            await websocket.send_json({"event": "error", "message": f"Invalid token: {str(e)}"})
            await websocket.close()
            return

        # Проверяем сообщение
        result = await db_session.execute(
            select(Message).filter_by(id=message_id, room_id=room_id)
        )
        message = result.scalar_one_or_none()

        if not message:
            await websocket.send_json({"event": "error", "message": "Message not found"})
            await websocket.close()
            return

        # Проверяем, является ли пользователь отправителем
        if message.sender_id != user_id:
            await websocket.send_json({"event": "error", "message": "You can only delete your own messages"})
            await websocket.close()
            return

        # Удаляем статусы прочтения
        await db_session.execute(
            delete(MessageReadStatus).where(MessageReadStatus.message_id == message_id)
        )

        # Удаляем сообщение
        await db_session.execute(
            delete(Message).where(Message.id == message_id)
        )
        await db_session.commit()

        # Уведомляем всех участников комнаты
        message_data = {
            "event": "message_deleted",
            "message_id": message_id,
            "room_id": room_id
        }
        for uid, ws in connected_users.items():
            try:
                await ws.send_json(message_data)
                print(f"Delete notification sent to user {uid} in room {room_id}")
            except Exception as e:
                print(f"Error notifying user {uid} in room {room_id}: {e}")

        await websocket.send_json({
            "event": "message_deleted",
            "status": "success",
            "message_id": message_id
        })

    except WebSocketDisconnect:
        print(f"⚫ User {user_id} disconnected from delete_message")
        await websocket.close()

    return JSONResponse(status_code=200, content={"message": "Message deleted successfully"})

@router_ws.websocket("/ws/clear_chat/{room_id}")
async def clear_chat(
    websocket: WebSocket,
    room_id: int,
    db_session: AsyncSession = Depends(get_db)
):
    await websocket.accept()
    user_id = None

    try:
        # Получаем токен
        data = await websocket.receive_json()
        token = data.get("token")

        if not token:
            await websocket.send_json({"event": "error", "message": "Missing token"})
            await websocket.close()
            return

        # Проверка токена
        try:
            user_id = await verify_access_token_for_user_id_ws(token)
        except Exception as e:
            await websocket.send_json({"event": "error", "message": f"Invalid token: {str(e)}"})
            await websocket.close()
            return

        # Проверяем, является ли пользователь участником комнаты
        result = await db_session.execute(
            select(RoomParticipant).filter_by(room_id=room_id, user_id=user_id)
        )
        participant = result.scalar_one_or_none()
        if not participant:
            await websocket.send_json({"event": "error", "message": "User not in this room"})
            await websocket.close()
            return

        # Удаляем все статусы прочтения
        await db_session.execute(
            delete(MessageReadStatus).where(
                MessageReadStatus.message_id.in_(
                    select(Message.id).filter_by(room_id=room_id)
                )
            )
        )

        # Удаляем все сообщения
        await db_session.execute(
            delete(Message).where(Message.room_id == room_id)
        )
        await db_session.commit()

        # Уведомляем всех участников комнаты
        message_data = {
            "event": "chat_cleared",
            "room_id": room_id
        }
        for uid, ws in connected_users.items():
            try:
                await ws.send_json(message_data)
                print(f"Chat clear notification sent to user {uid} in room {room_id}")
            except Exception as e:
                print(f"Error sending clear notification to user {uid} in room {room_id}: {e}")

        # Подтверждаем отправителю
        await websocket.send_json({
            "event": "chat_cleared",
            "room_id": room_id
        })

    except WebSocketDisconnect:
        print(f"⚫ User {user_id} disconnected from clear_chat")
        await websocket.close()

    return JSONResponse(status_code=200, content={"message": "Chat cleared successfully"})