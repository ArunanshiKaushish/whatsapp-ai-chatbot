"""Database engine, session factory, and initialization."""

import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from config import Config
from models import Base, Message, User, utcnow

logger = logging.getLogger(__name__)

engine = create_engine(
    Config.DATABASE_URL,
    connect_args={"check_same_thread": False}
    if Config.DATABASE_URL.startswith("sqlite")
    else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized at %s", Config.DATABASE_URL)


def get_or_create_user(session: Session, phone_number: str) -> User:
    """Fetch user by phone number or create a new record."""
    user = session.scalar(select(User).where(User.phone_number == phone_number))
    if user is None:
        user = User(phone_number=phone_number)
        session.add(user)
        session.flush()
        logger.info("Created new user: %s", phone_number)
    else:
        user.last_seen = utcnow()
    return user


def save_message(session: Session, user_id: int, role: str, content: str) -> Message:
    """Persist a chat message."""
    message = Message(user_id=user_id, role=role, content=content.strip())
    session.add(message)
    session.flush()
    return message


def get_recent_messages(session: Session, user_id: int, limit: int) -> list[Message]:
    """Return the most recent messages for a user in chronological order."""
    messages = session.scalars(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.timestamp.desc())
        .limit(limit)
    ).all()
    return list(reversed(messages))
