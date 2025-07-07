"""Database models for the Noteflow notes app."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# PUBLIC_INTERFACE
class User(Base):
    """The User model representing authenticated users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    hashed_password = Column(String(128), nullable=False)
    # Optionally: email, created_at, etc.

    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")

# PUBLIC_INTERFACE
class Note(Base):
    """The Note model storing user-created notes."""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    owner = relationship("User", back_populates="notes")
