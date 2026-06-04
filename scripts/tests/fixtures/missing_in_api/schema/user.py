from pydantic import BaseModel


class ForgottenModel(BaseModel):
    name: str
