from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

# Database URL for SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./super_private_chat.db"

# Create a new SQLite database engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()

# Database model for users
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, phone_number={self.phone_number})>"

# Database model for messages (renamed to MessageDB to avoid confusion with Pydantic model)
class MessageDB(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    encrypted_message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    def __repr__(self):
        return f"<MessageDB(id={self.id}, sender={self.sender}, recipient={self.recipient})>"

    def set_expiry(self, expires_in: int):
        """Set the expiration time of the message."""
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

# Initialize the database
def init_db():
    """Create database tables."""
    Base.metadata.create_all(bind=engine)

# Create a database session
def get_db():
    """Get a new database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
