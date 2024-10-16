from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from app.models import Message, UserCreate, UserLogin
from app.auth import create_user, authenticate_user, create_access_token, get_current_user
from app.database import get_db, Message as MessageModel, init_db
from app.utils import encrypt_message, decrypt_message
from datetime import datetime, timedelta
import asyncio
import os
import logging
from dotenv import load_dotenv  # Import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk

sentry_sdk.init(
    dsn="https://a2c3921a52ca4567e6cf54aa102099ee@o4508129078542336.ingest.us.sentry.io/4508129081032704",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=0.2,  # Sample 20% of transactions for performance tracing
    profiles_sample_rate=0.1,  # Sample 10% of transactions for profiling
)





# Load environment variables from .env file
load_dotenv()

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

# Log the API key (for debugging purposes, remove or obfuscate in production)
if API_KEY:
    logging.info("Loaded API_KEY: [PROTECTED]")  # Obfuscate for security
else:
    logging.error("API_KEY not found in environment variables.")

# Initialize the database
init_db()

# Function to verify the API key against the stored API key
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
        db: Session = next(get_db())  # Get a session to use in the task
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

# Send message (message stored until read)
@app.post("/send/")
async def send_message(message: Message, token: str = Depends(get_current_user), db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    expiration_time = datetime.utcnow() + timedelta(seconds=message.expires_in)

    # Encrypt the message before storing it
    encrypted_msg = encrypt_message(message.encrypted_message)

    db_message = MessageModel(
        sender=message.sender,
        recipient=message.recipient,
        encrypted_message=encrypted_msg,
        expires_at=expiration_time
    )
    db.add(db_message)
    db.commit()
    return {"status": "Message sent"}

# Receive message and mark it as read
@app.get("/receive/{recipient}")
async def receive_message(recipient: str, token: str = Depends(get_current_user), db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    message = db.query(MessageModel).filter(MessageModel.recipient == recipient).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="No message for recipient")

    # Decrypt the message
    try:
        decrypted_msg = decrypt_message(message.encrypted_message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decrypt message: {str(e)}")

    # Delete the message from the database after it has been read
    db.delete(message)
    db.commit()

    return {"decrypted_message": decrypted_msg}

# Check message read status (if needed)
@app.get("/message_status/{recipient}")
async def message_status(recipient: str, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    message = db.query(MessageModel).filter(MessageModel.recipient == recipient).first()
    if message:
        return {"status": "Message exists"}
    return {"status": "No message for recipient"}
