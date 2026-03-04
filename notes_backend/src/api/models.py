"""
SQLAlchemy ORM models for the NoteMaster database schema.
Maps to existing tables: users, notes, tags, note_tags, sync_logs.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.api.database import Base


class User(Base):
    """User account model for authentication and sync."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(150), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    # Relationships
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="user", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="user", cascade="all, delete-orphan")


class Note(Base):
    """Note model with support for soft delete, pinning, archiving."""
    __tablename__ = "notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(500), nullable=False, default="")
    content = Column(Text, nullable=False, default="")
    content_type = Column(String(50), nullable=False, default="markdown")
    is_pinned = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    local_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="notes")
    note_tags = relationship("NoteTag", back_populates="note", cascade="all, delete-orphan")


class Tag(Base):
    """Tag model, unique per user."""
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    color = Column(String(7), default="#3b82f6")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tags_user_name"),)

    # Relationships
    user = relationship("User", back_populates="tags")
    note_tags = relationship("NoteTag", back_populates="tag", cascade="all, delete-orphan")


class NoteTag(Base):
    """Junction table for many-to-many notes <-> tags relationship."""
    __tablename__ = "note_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id = Column(UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("note_id", "tag_id", name="uq_note_tags"),)

    # Relationships
    note = relationship("Note", back_populates="note_tags")
    tag = relationship("Tag", back_populates="note_tags")


class SyncLog(Base):
    """Sync log model for tracking offline-first sync operations."""
    __tablename__ = "sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    sync_status = Column(String(30), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    client_timestamp = Column(DateTime(timezone=True), nullable=True)
    server_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="sync_logs")
