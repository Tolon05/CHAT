import os
import sys
import subprocess
import signal
from jose import jwt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.database import create_tables, engine
from backend.auth.routes import router
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from backend.config import settings
from backend.token_utils import verify_access_token



async def lifespan(app: FastAPI):
    print("Приложение запускается...")
    await create_tables() 

    global celery_process

    print("🚀 Приложение запускается...")

    print("🔧 Запуск Celery worker...")
    celery_process = subprocess.Popen([
        "celery",
        "-A", "backend.celery_worker.celery",
        "worker",
        "--loglevel=info", 
        "--concurrency=1",  
        "--pool=solo",      # Для Windows, чтобы избежать ошибок с многопроцессностью
    ])


    yield  
    await engine.dispose() 
    print("Приложение завершает работу...")

    if celery_process:
        print("🛑 Остановка Celery worker...")
        celery_process.send_signal(signal.SIGTERM)
        celery_process.wait()


app = FastAPI(lifespan=lifespan)

class RefreshMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        allowed_paths = ["/refresh", "/login", "/register", "/favicon.ico", "/verify"]
        if request.url.path.startswith("/static") or request.url.path in allowed_paths:
            return await call_next(request)
        
        access_token = request.cookies.get("access_token")
        refresh_token = request.cookies.get("refresh_token")

        if access_token:
            print("Access token found")
            try:
                user_id = await verify_access_token(access_token)
                if user_id:
                    request.state.user_id = user_id
                    return await call_next(request)
            except jwt.ExpiredSignatureError:
                return RedirectResponse("/refresh")

        elif refresh_token:
            print("Refresh token found")
            return RedirectResponse("/refresh")

        return RedirectResponse("/login")

app.add_middleware(RefreshMiddleware)

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

@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    print("Загружаем страницу login.html")
    return templates.TemplateResponse("login.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
