import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.database import create_tables, engine
from backend.auth.routes import router
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
# from celery_worker import celery
from backend.config import settings

async def lifespan(app: FastAPI):
    print("Приложение запускается...")
    await create_tables() 
    yield  
    await engine.dispose() 
    print("Приложение завершает работу...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любого домена
    allow_credentials=True,  # cookies, authorization headers, etc.
    allow_methods=["*"],  # Разрешаем все HTTP-методы
    allow_headers=["*"],  # Разрешаем все заголовки
)

app.include_router(router)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "templates"))

@app.get("/", response_class=HTMLResponse)
async def login_form(request: Request):
    print("Загружаем страницу login.html")
    return templates.TemplateResponse("login.html", {"request": request})

# # Для Celery настройки
# @app.on_event("startup")
# async def startup_event():
#     # Здесь можно подключить Celery и выполнить инициализацию, если нужно
#     pass

# @app.on_event("shutdown")
# async def shutdown_event():
#     # Здесь можно выполнить завершение работы и очистку ресурсов
#     pass

# Стартуем сервер с помощью Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
