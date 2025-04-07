from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)

    # Загрузка конфигурации из config.py
    app.config.from_object("config.Config")

    # Инициализация расширений
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # Регистрация маршрутов
    from app.routes import main

    app.register_blueprint(main)

    return app
