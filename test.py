from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from backend.database.models import User  # Убедись, что модель User импортируется правильно

engine = create_engine("sqlite:///app.db")  # Без async

with Session(engine) as session:
    users = session.execute(select(User)).scalars().all()
    for user in users:
        print(user)