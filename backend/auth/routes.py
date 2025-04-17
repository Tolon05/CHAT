# import sys
import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates  # Импортируем Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import SessionLocal, get_db
from backend.models import User, EmailCode, Device
from backend.security import hash_password, verify_password
from backend.tasks import send_verification_email
import random, datetime
from backend.token_utils import create_access_token, create_refresh_token
from backend.session_utils import store_session, get_session, store_verification_code, verify_code, delete_verification_code

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "templates"))

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
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    print("User does not exist")

    code = str(random.randint(1000, 9999))

    await store_verification_code(email, code, expires_minutes=5)

    await send_verification_email(email, code)

    request.session["username"] = username
    request.session["email"] = email
    request.session["password"] = hash_password(password)
    
    return RedirectResponse("/verify", status_code=303)

@router.get("/verify", response_class=HTMLResponse)
async def verify_form(request: Request):
    print("Загружаем страницу verify.html")
    return templates.TemplateResponse("verify.html", {"request": request})

# @router.post("/verify")
# async def verify(request: Request, code: str = Form(...), db: Session = Depends(get_db)):
#     email = request.session.get("email")
#     record = db.query(EmailCode).filter(EmailCode.email == email).order_by(EmailCode.expires_at.desc()).first()

#     if not record or record.code != code or record.expires_at < datetime.datetime.utcnow():
#         raise HTTPException(status_code=400, detail="Код недействителен или просрочен")

#     user = User(username=request.session["username"], email=email, hashed_password=request.session["password"], is_verified=True)
#     db.add(user)
#     db.commit()

#     return RedirectResponse("/login", status_code=303)

# @router.post("/login")
# async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.username == username).first()

#     if not user or not verify_password(password, user.hashed_password):
#         raise HTTPException(status_code=400, detail="Неверные учетные данные")

#     access_token = create_access_token(user.id)
#     refresh_token = create_refresh_token(user.id)

#     store_session(user.id, {"access_token": access_token, "refresh_token": refresh_token})

#     return {"access_token": access_token, "refresh_token": refresh_token}

# @router.get("/dashboard", response_class=HTMLResponse)
# async def dashboard(request: Request, db: Session = Depends(get_db)):
#     user_id = request.session.get("user_id")
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Не авторизован")

#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="Пользователь не найден")

#     devices = db.query(Device).filter(Device.user_id == user_id).all()

#     return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "devices": devices})

# @router.post("/add_device")
# async def add_device(request: Request, device_info: str = Form(...), db: Session = Depends(get_db)):
#     user_id = request.session.get("user_id")
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Не авторизован")

#     device = Device(user_id=user_id, device_info=device_info, ip_address=request.client.host)
#     db.add(device)
#     db.commit()

#     return RedirectResponse("/dashboard", status_code=303)
