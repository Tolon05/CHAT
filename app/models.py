from app import db
import datetime


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    otp_secret = db.Column(db.String(16), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
