from fastapi import FastAPI
from app.routes import users
from app import models
from app.database import engine

app = FastAPI()
app.include_router(users.router)
models.Base.metadata.create_all(bind=engine)