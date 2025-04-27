# import sys
import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import APIRouter, Request, Form, Depends, HTTPException, Response, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates  
from sqlalchemy.future import select
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from backend.database import get_db
from backend.models.models import User, Contact, ChatRoom, RoomParticipant, Message
from backend.auth.token_utils import verify_access_token_for_user_id
from sqlalchemy import or_, and_
from sqlalchemy.sql import exists
from pathlib import Path
import shutil
import base64

router_dash = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "templates"))

def b64encode_filter(value: bytes) -> str:
    return base64.b64encode(value).decode('utf-8')

# Регистрируем собственный фильтр
templates.env.filters['b64encode'] = b64encode_filter

@router_dash.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(verify_access_token_for_user_id),
    selected_contact_id: int = None,
):
    request.state.user_id = current_user_id
    message_exists = exists().where(Message.room_id == ChatRoom.id).correlate(ChatRoom)
    selected_contact = None
    contact_data_dict = {}

    if selected_contact_id:
        selected_contact_result = await db.execute(
            select(Contact, User)
            .join(User, User.id == Contact.contact_id)
            .where(Contact.id == selected_contact_id)
        )
        selected_contact = selected_contact_result.first()  # (Contact, User)

    result = await db.execute(
        select(ChatRoom, User)
        .select_from(ChatRoom)
        .outerjoin(RoomParticipant, RoomParticipant.room_id == ChatRoom.id)
        .outerjoin(Message, Message.room_id == ChatRoom.id)
        .outerjoin(Contact, and_(Contact.owner_id == current_user_id))  
        .outerjoin(User, User.id == Contact.contact_id)  
        .where(
            or_(
                and_(
                    RoomParticipant.user_id == current_user_id,
                    message_exists
                ),
                and_(
                    RoomParticipant.user_id == current_user_id,
                    ChatRoom.type != "private"
                )
            )
        )
        .group_by(ChatRoom.id, User.id)
    )

    chats_with_contacts = result.all()

    if selected_contact:
        contact_obj, user_obj = selected_contact

        user_ids = {user.id for room, user in chats_with_contacts if user}
        if user_obj.id not in user_ids:
            chats_with_contacts.insert(0, (None, user_obj))

        contact_data_dict[user_obj.id] = user_obj

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "contacts": chats_with_contacts,
            "selected_contact": selected_contact,
            "selected_contact_user": selected_contact[1],
            "contact_data_dict": contact_data_dict, 
        }, 
        response=response
    )

@router_dash.get("/add_con", response_class=HTMLResponse)
async def add_con_page(request: Request, db: AsyncSession = Depends(get_db), current_user_id: int = Depends(verify_access_token_for_user_id)):
    result = await db.execute(
        select(User)
        .join(Contact, Contact.contact_id == User.id)
        .where(Contact.owner_id == current_user_id)
    )
    contacts = result.scalars().all()
    return templates.TemplateResponse("add_contacts.html", {"request": request, "contacts": contacts})

@router_dash.get("/new_con", response_class=HTMLResponse)
async def new_con_page(request: Request, db: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse("new_contact.html", {"request": request})


@router_dash.post("/add_new_contact")
async def add_contact(
    request: Request,
    username: str = Form(...),
    session: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(verify_access_token_for_user_id)
):
    ContactAlias = aliased(Contact)

    result = await session.execute(
        select(User, ContactAlias)
        .outerjoin(
            ContactAlias,
            (ContactAlias.owner_id == current_user_id) & (ContactAlias.contact_id == User.id)
        )
        .where(User.username == username)
    )

    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    target_user, existing_contact = row

    if target_user.id == current_user_id:
        raise HTTPException(status_code=400, detail="Нельзя добавить себя в контакты")

    if existing_contact:
        raise HTTPException(status_code=400, detail="Контакт уже добавлен")

    contact = Contact(owner_id=current_user_id, contact_id=target_user.id)
    session.add(contact)
    await session.commit()

    return RedirectResponse(url="/dash/new_con", status_code=303)

@router_dash.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(verify_access_token_for_user_id)
):
    result = await db.execute(select(User).where(User.id == current_user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    avatar_url = None
    if user.avatar_data:
        avatar_url = "data:image/png;base64," + base64.b64encode(user.avatar_data).decode('utf-8')
        print("Avatar URL:", avatar_url)

    print("avatarrrrrr", avatar_url)
    print("user", user)


    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": {
            "username": user.username,
            "email": user.email,
            "about": user.about,
            "avatar_url": avatar_url
        }
    })

@router_dash.post("/profile/update")
async def update_profile(
    request: Request,
    username: str = Form(...),
    email: str = Form(None),
    about: str = Form(None),
    status: str = Form(None),
    avatar: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(verify_access_token_for_user_id)
):

    try:
        result = await db.execute(select(User).where(User.id == current_user_id))
        user = result.scalar_one()

        # Обновление текстовых данных
        user.username = username
        user.email = email
        user.about = about
        user.status = status

        # Обновление аватара
        if avatar and avatar.filename:
            avatar_bytes = await avatar.read()
            user.avatar_data = avatar_bytes
            print("Avatar updated")
            print(avatar.filename)

        await db.commit()
        print("Changes saved to DB")
        return RedirectResponse(url="/dash/profile", status_code=303)

    except Exception as e:
        await db.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))