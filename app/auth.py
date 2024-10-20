from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.database import SessionLocal, User
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dependency for getting the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create a new user
def create_user(db: Session, phone_number: str, password: str):
    hashed_password = pwd_context.hash(password)
    user = User(phone_number=phone_number, password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user  # Optional: return the created user

# Authenticate user by checking their password
def authenticate_user(db: Session, phone_number: str, password: str):
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user or not pwd_context.verify(password, user.password):
        return False
    return user

# Create a non-expiring JWT token
def create_access_token(data: dict):
    to_encode = data.copy()
    # Do not include 'exp' claim
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Get current authenticated user from the token
def get_current_user(token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Invalid credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone_number: str = payload.get("sub")
        if phone_number is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if user is None:
        raise credentials_exception
    return user
