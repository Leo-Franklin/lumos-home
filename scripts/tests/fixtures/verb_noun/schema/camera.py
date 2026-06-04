from pydantic import BaseModel


class CameraCreate(BaseModel):
    name: str
    url: str


class CameraOut(BaseModel):
    id: int
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str
