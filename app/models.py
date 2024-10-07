from pydantic import BaseModel

# Message data model
class Message(BaseModel):
    sender: str
    recipient: str
    encrypted_message: str
    expires_in: int  # Time in seconds before message self-destructs

# User registration model
class UserCreate(BaseModel):
    phone_number: str
    password: str

# User login model
class UserLogin(BaseModel):
    phone_number: str
    password: str
