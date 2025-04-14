from pydantic import BaseModel
from typing import List, Optional

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: int
    hashed_password: str
    is_verified: bool

    class Config:
        orm_mode = True

class DeviceBase(BaseModel):
    device_info: str
    ip_address: str

class DeviceCreate(DeviceBase):
    pass

class Device(DeviceBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: int
    username: str
