"""
Pydantic schemas for request/response validation.
Defines data transfer objects for auth, notes, tags, and sync operations.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


# =============================================================================
# AUTH SCHEMAS
# =============================================================================

class UserRegister(BaseModel):
    """Schema for user registration request."""
    username: str = Field(..., min_length=3, max_length=100, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, max_length=128, description="User password")
    display_name: Optional[str] = Field(None, max_length=150, description="Display name")


class UserLogin(BaseModel):
    """Schema for user login request."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """Schema for user data in responses."""
    id: UUID = Field(..., description="User UUID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    display_name: Optional[str] = Field(None, description="Display name")
    created_at: datetime = Field(..., description="Account creation timestamp")
    is_active: bool = Field(..., description="Whether account is active")

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema for JWT token response after login/register."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="User details")


# =============================================================================
# TAG SCHEMAS
# =============================================================================

class TagCreate(BaseModel):
    """Schema for creating a tag."""
    name: str = Field(..., min_length=1, max_length=100, description="Tag name")
    color: Optional[str] = Field("#3b82f6", max_length=7, description="Tag color hex code")


class TagUpdate(BaseModel):
    """Schema for updating a tag."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Tag name")
    color: Optional[str] = Field(None, max_length=7, description="Tag color hex code")


class TagResponse(BaseModel):
    """Schema for tag data in responses."""
    id: UUID = Field(..., description="Tag UUID")
    name: str = Field(..., description="Tag name")
    color: Optional[str] = Field(None, description="Tag color hex code")
    created_at: datetime = Field(..., description="Tag creation timestamp")

    model_config = {"from_attributes": True}


# =============================================================================
# NOTE SCHEMAS
# =============================================================================

class NoteCreate(BaseModel):
    """Schema for creating a note."""
    title: str = Field("", max_length=500, description="Note title")
    content: str = Field("", description="Note content (markdown/rich text)")
    content_type: str = Field("markdown", max_length=50, description="Content type")
    is_pinned: bool = Field(False, description="Whether note is pinned")
    is_archived: bool = Field(False, description="Whether note is archived")
    local_id: Optional[str] = Field(None, max_length=255, description="Client-side local ID")
    tag_ids: Optional[List[UUID]] = Field(None, description="List of tag UUIDs to attach")


class NoteUpdate(BaseModel):
    """Schema for updating a note."""
    title: Optional[str] = Field(None, max_length=500, description="Note title")
    content: Optional[str] = Field(None, description="Note content")
    content_type: Optional[str] = Field(None, max_length=50, description="Content type")
    is_pinned: Optional[bool] = Field(None, description="Whether note is pinned")
    is_archived: Optional[bool] = Field(None, description="Whether note is archived")
    tag_ids: Optional[List[UUID]] = Field(None, description="List of tag UUIDs to attach")


class NoteResponse(BaseModel):
    """Schema for note data in responses."""
    id: UUID = Field(..., description="Note UUID")
    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Note content")
    content_type: str = Field(..., description="Content type")
    is_pinned: bool = Field(..., description="Whether note is pinned")
    is_archived: bool = Field(..., description="Whether note is archived")
    is_deleted: bool = Field(..., description="Whether note is soft-deleted")
    local_id: Optional[str] = Field(None, description="Client-side local ID")
    created_at: datetime = Field(..., description="Note creation timestamp")
    updated_at: datetime = Field(..., description="Note last update timestamp")
    tags: List[TagResponse] = Field(default_factory=list, description="Attached tags")

    model_config = {"from_attributes": True}


class NoteListResponse(BaseModel):
    """Schema for paginated notes list response."""
    notes: List[NoteResponse] = Field(..., description="List of notes")
    total: int = Field(..., description="Total number of matching notes")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of notes per page")


# =============================================================================
# SYNC SCHEMAS
# =============================================================================

class SyncNoteItem(BaseModel):
    """Schema for a single note in a sync push request."""
    local_id: str = Field(..., description="Client-side local ID")
    title: str = Field("", description="Note title")
    content: str = Field("", description="Note content")
    content_type: str = Field("markdown", description="Content type")
    is_pinned: bool = Field(False, description="Whether note is pinned")
    is_archived: bool = Field(False, description="Whether note is archived")
    is_deleted: bool = Field(False, description="Whether note is soft-deleted")
    updated_at: datetime = Field(..., description="Client-side last update timestamp")
    tag_names: Optional[List[str]] = Field(None, description="Tag names to attach")


class SyncPushRequest(BaseModel):
    """Schema for sync push request (client -> server)."""
    notes: List[SyncNoteItem] = Field(..., description="Notes to push to server")
    last_sync_at: Optional[datetime] = Field(None, description="Last successful sync timestamp")


class SyncPullResponse(BaseModel):
    """Schema for sync pull response (server -> client)."""
    notes: List[NoteResponse] = Field(..., description="Notes updated since last sync")
    server_timestamp: datetime = Field(..., description="Current server timestamp")


class SyncPushResponse(BaseModel):
    """Schema for sync push response."""
    synced_count: int = Field(..., description="Number of notes synced")
    errors: List[str] = Field(default_factory=list, description="Any sync errors")
    server_timestamp: datetime = Field(..., description="Current server timestamp")
