from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_verified = Column(Boolean, default=False)
    devices = relationship("Device", back_populates="user")

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    device_info = Column(String)
    ip_address = Column(String)
    last_login = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="devices")

class EmailCode(Base):
    __tablename__ = "email_codes"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String)
    code = Column(String)
    expires_at = Column(DateTime)
