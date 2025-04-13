from pydantic import BaseModel

class UserBase(BaseModel):
    username: str
    phone_number: str | None = None
    password : str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    class Config:
        orm_mode = True
