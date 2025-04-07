class Config:
    SQLALCHEMY_DATABASE_URI = "postgresql://user:password@localhost/messenger_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "supersecretkey"  # Вы можете заменить на более безопасный ключ
