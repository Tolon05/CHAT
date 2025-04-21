# import sys
import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import APIRouter, Request, Form, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates  
from sqlalchemy.future import select
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from backend.database import get_db
from backend.models.models import User, Contact
from backend.auth.token_utils import verify_access_token_for_user_id

router_dash = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "templates"))

@router_dash.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse("dashboard.html", {"request": request})

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
