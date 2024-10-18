from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from app.models import Message, UserCreate, UserLogin
from app.auth import create_user, authenticate_user, create_access_token, get_current_user
from app.database import get_db, MessageDB as MessageModel, init_db
from datetime import datetime, timedelta
import asyncio
import os
import logging
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from app.helpers.time import format_received_time
import sentry_sdk

# Load environment variables from .env file
load_dotenv()

# Sentry initialization
sentry_sdk.init(
    dsn=os.getenv("DSN"),
    traces_sample_rate=0.2,
    profiles_sample_rate=0.1,
)

app = FastAPI()

# Add CORS middleware to allow requests from all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up logging
logging.basicConfig(level=logging.INFO)

# API Key configuration
API_KEY_NAME = "access_token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Fetch the API key from environment variables
API_KEY = os.getenv("API_KEY")

if API_KEY:
    logging.info("Loaded API_KEY: [PROTECTED]")  # Obfuscate for security
else:
    logging.error("API_KEY not found in environment variables.")

# Initialize the database
init_db()

# Verify the API key
async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
    )

# Background task to delete expired messages
async def delete_expired_messages():
    while True:
        await asyncio.sleep(10)  # Check every 10 seconds
        current_time = datetime.utcnow()
        db: Session = next(get_db())
        expired_messages = db.query(MessageModel).filter(MessageModel.expires_at < current_time).all()

        for message in expired_messages:
            db.delete(message)
        db.commit()

# Start the background task
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(delete_expired_messages())

# Register user route
@app.post("/register/")
async def register_user(user: UserCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    create_user(db, user.phone_number, user.password)
    return {"status": "User registered successfully"}

# Login and generate access token
@app.post("/token")
async def login(user: UserLogin, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    db_user = authenticate_user(db, user.phone_number, user.password)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": db_user.phone_number})
    return {"access_token": access_token, "token_type": "bearer"}

# Send message (sender name automatically uses the authenticated user's name)
@app.post("/send/")
async def send_message(
    message: Message,
    token: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    sender_name = token.phone_number
    expiration_time = datetime.utcnow() + timedelta(seconds=message.expires_in)

    db_message = MessageModel(
        sender=sender_name,
        recipient=message.recipient,
        encrypted_message=message.encrypted_message,  # Store the message as plain text
        expires_at=expiration_time
    )
    db.add(db_message)
    db.commit()

    return {"status": "Message sent successfully", "sender": sender_name}

# Receive all messages for the recipient (automatically fetch the recipient based on the authenticated user)
@app.get("/receive/")
async def receive_message(token: str = Depends(get_current_user), db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    recipient = token.phone_number  # Automatically use the authenticated user's phone number as the recipient
    messages = db.query(MessageModel).filter(MessageModel.recipient == recipient).all()

    if not messages:
        raise HTTPException(status_code=404, detail="No messages for recipient")

    received_messages = []

    for message in messages:
        received_messages.append({
            "sender": message.sender,
            "decrypted_message": message.encrypted_message,  # No decryption needed, it's stored as plain text
            "received_at": format_received_time(datetime.utcnow())
        })

        db.delete(message)

    db.commit()
    return {"messages": received_messages}

# Check message read status
@app.get("/message_status/")
async def message_status(token: str = Depends(get_current_user), db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    recipient = token.phone_number  # Automatically use the authenticated user's phone number as the recipient
    message = db.query(MessageModel).filter(MessageModel.recipient == recipient).first()
    if message:
        return {"status": "Message exists"}
    return {"status": "No message for recipient"}
