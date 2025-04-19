# import sys
import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import APIRouter, Request, Form, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates  # Импортируем Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import SessionLocal, get_db
from backend.models import User, EmailCode, Device
from backend.security import hash_password, verify_password
from backend.tasks import send_verification_email_task
import random, datetime
from backend.token_utils import create_access_token, create_refresh_token, verify_refresh_token
from backend.session_utils import store_access_token, store_refresh_token, get_session, store_verification_code, verify_code
from datetime import timedelta

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "templates"))

@router.get("/refresh")
async def refresh_token(request: Request, response: Response):
    print("Обновляем токен")
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        return RedirectResponse("/login")

    user_id = await verify_refresh_token(refresh_token)
    if not user_id:
        return RedirectResponse("/login")

    new_access_token = await create_access_token({"user_id": user_id})
    expiration_time_access = timedelta(minutes=1)

    await store_access_token(user_id, new_access_token, expiration_time_access)

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        max_age=expiration_time_access,
        httponly=True,
        # secure=True,
        samesite="Strict"
    )
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    print("Загружаем страницу register.html")
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    query = select(User).where(or_(User.username == username, User.email == email))
    result = await db.execute(query)
    user = result.scalars().first()
    if user:
        print("Пользователь уже существует:", user)
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    print("User does not exist")

    code = str(random.randint(1000, 9999))

    await store_verification_code(email, code, expires_minutes=5)

    send_verification_email_task.apply_async(args=[email, code])

    request.session["username"] = username
    request.session["email"] = email
    request.session["password"] = hash_password(password)
    
    return RedirectResponse("/verify", status_code=303)

@router.get("/verify", response_class=HTMLResponse)
async def verify_form(request: Request):
    print("Загружаем страницу verify.html")
    return templates.TemplateResponse("verify.html", {"request": request})

@router.post("/verify")
async def verify(request: Request, code: str = Form(...), db: AsyncSession = Depends(get_db)):
    email = request.session.get("email")

    if not await verify_code(email, code): 
        print("❌ Неверный код:", code)
        raise HTTPException(status_code=400, detail="Код недействителен или просрочен")

    user = User(
        username=request.session["username"],
        email=email,
        hashed_password=request.session["password"],
        is_verified=True
    )

    db.add(user)
    await db.commit()          
    await db.refresh(user)      

    print("✅ Пользователь сохранён:", user)
    return RedirectResponse("/", status_code=303)

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    user = result.scalars().first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверные учетные данные")

    access_token = await create_access_token({"user_id": user.id})
    refresh_token = await create_refresh_token({"user_id": user.id})

    expiration_time_refresh = timedelta(minutes=2)
    expiration_time_access = timedelta(minutes=1)

    response = RedirectResponse("/", status_code=303)
    
    response.set_cookie(key="access_token", value=access_token, max_age=expiration_time_access, httponly=True, samesite="Strict") # secure=True,
    response.set_cookie(key="refresh_token", value=refresh_token, max_age=expiration_time_refresh, httponly=True, samesite="Strict")

    await store_access_token(user.id, access_token, expiration_time_access)
    await store_refresh_token(user.id, refresh_token, expiration_time_refresh)

    return RedirectResponse("/", status_code=303)

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Не авторизован")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    devices = db.query(Device).filter(Device.user_id == user_id).all()

    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "devices": devices})

# @router.post("/add_device")
# async def add_device(request: Request, device_info: str = Form(...), db: Session = Depends(get_db)):
#     user_id = request.session.get("user_id")
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Не авторизован")

#     device = Device(user_id=user_id, device_info=device_info, ip_address=request.client.host)
#     db.add(device)
#     db.commit()

#     return RedirectResponse("/dashboard", status_code=303)
