"""
Notes CRUD routes for the NoteMaster API.
Provides endpoints for creating, reading, updating, deleting, listing, and searching notes.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.models import Note, NoteTag, Tag, User
from src.api.schemas import NoteCreate, NoteUpdate, NoteResponse, NoteListResponse, TagResponse
from src.api.auth import get_current_user

router = APIRouter(prefix="/notes", tags=["Notes"])


def _note_to_response(note: Note) -> NoteResponse:
    """Convert a Note ORM object to a NoteResponse schema, including tags."""
    tags = []
    for nt in note.note_tags:
        tags.append(TagResponse.model_validate(nt.tag))
    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        content_type=note.content_type,
        is_pinned=note.is_pinned,
        is_archived=note.is_archived,
        is_deleted=note.is_deleted,
        local_id=note.local_id,
        created_at=note.created_at,
        updated_at=note.updated_at,
        tags=tags,
    )


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=NoteListResponse,
    summary="List notes",
    description="List all notes for the authenticated user with pagination, filtering, and sorting.",
    responses={
        401: {"description": "Authentication required"},
    },
)
def list_notes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Notes per page"),
    is_archived: Optional[bool] = Query(None, description="Filter by archived status"),
    is_pinned: Optional[bool] = Query(None, description="Filter by pinned status"),
    tag_id: Optional[UUID] = Query(None, description="Filter by tag UUID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List notes for the current user with pagination and optional filters.

    Args:
        page: Page number (1-indexed).
        page_size: Number of notes per page.
        is_archived: Optional filter for archived notes.
        is_pinned: Optional filter for pinned notes.
        tag_id: Optional filter by tag UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Paginated list of notes with total count.
    """
    query = db.query(Note).filter(
        Note.user_id == current_user.id,
        Note.is_deleted == False,
    )

    # Apply optional filters
    if is_archived is not None:
        query = query.filter(Note.is_archived == is_archived)
    if is_pinned is not None:
        query = query.filter(Note.is_pinned == is_pinned)
    if tag_id is not None:
        query = query.join(NoteTag).filter(NoteTag.tag_id == tag_id)

    # Get total count before pagination
    total = query.count()

    # Order by pinned first, then by updated_at descending
    query = query.order_by(Note.is_pinned.desc(), Note.updated_at.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    notes = query.offset(offset).limit(page_size).all()

    return NoteListResponse(
        notes=[_note_to_response(n) for n in notes],
        total=total,
        page=page,
        page_size=page_size,
    )


# PUBLIC_INTERFACE
@router.get(
    "/search",
    response_model=NoteListResponse,
    summary="Search notes",
    description="Full-text search across note titles and content using PostgreSQL tsvector.",
    responses={
        401: {"description": "Authentication required"},
    },
)
def search_notes(
    q: str = Query(..., min_length=1, description="Search query string"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Notes per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search notes by title and content using PostgreSQL full-text search.

    Args:
        q: The search query string.
        page: Page number (1-indexed).
        page_size: Number of notes per page.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Paginated list of matching notes.
    """
    # Use PostgreSQL full-text search on title and content
    search_filter = or_(
        func.to_tsvector("english", Note.title).match(q),
        func.to_tsvector("english", Note.content).match(q),
        Note.title.ilike(f"%{q}%"),
        Note.content.ilike(f"%{q}%"),
    )

    query = db.query(Note).filter(
        Note.user_id == current_user.id,
        Note.is_deleted == False,
        search_filter,
    )

    total = query.count()

    offset = (page - 1) * page_size
    notes = query.order_by(Note.updated_at.desc()).offset(offset).limit(page_size).all()

    return NoteListResponse(
        notes=[_note_to_response(n) for n in notes],
        total=total,
        page=page,
        page_size=page_size,
    )


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new note",
    description="Create a new note with optional tags for the authenticated user.",
    responses={
        401: {"description": "Authentication required"},
    },
)
def create_note(
    data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new note.

    Args:
        data: Note creation data.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        The created note with tags.
    """
    note = Note(
        user_id=current_user.id,
        title=data.title,
        content=data.content,
        content_type=data.content_type,
        is_pinned=data.is_pinned,
        is_archived=data.is_archived,
        local_id=data.local_id,
    )
    db.add(note)
    db.flush()  # Get note.id before adding tags

    # Attach tags if provided
    if data.tag_ids:
        for tag_id in data.tag_ids:
            # Verify tag belongs to user
            tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
            if tag:
                note_tag = NoteTag(note_id=note.id, tag_id=tag.id)
                db.add(note_tag)

    db.commit()
    db.refresh(note)

    return _note_to_response(note)


# PUBLIC_INTERFACE
@router.get(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Get a single note",
    description="Retrieve a specific note by its UUID.",
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "Note not found"},
    },
)
def get_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific note by ID.

    Args:
        note_id: The UUID of the note to retrieve.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        The requested note with tags.
    """
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id,
        Note.is_deleted == False,
    ).first()

    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    return _note_to_response(note)


# PUBLIC_INTERFACE
@router.put(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Update a note",
    description="Update an existing note's title, content, tags, or status flags.",
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "Note not found"},
    },
)
def update_note(
    note_id: UUID,
    data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing note.

    Args:
        note_id: The UUID of the note to update.
        data: Fields to update (only non-None fields are applied).
        current_user: Authenticated user.
        db: Database session.

    Returns:
        The updated note with tags.
    """
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id,
        Note.is_deleted == False,
    ).first()

    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    # Update non-None fields
    update_data = data.model_dump(exclude_unset=True, exclude={"tag_ids"})
    for field, value in update_data.items():
        setattr(note, field, value)

    note.updated_at = datetime.now(timezone.utc)

    # Update tags if provided
    if data.tag_ids is not None:
        # Remove existing note_tags
        db.query(NoteTag).filter(NoteTag.note_id == note.id).delete()
        # Add new tags
        for tag_id in data.tag_ids:
            tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
            if tag:
                note_tag = NoteTag(note_id=note.id, tag_id=tag.id)
                db.add(note_tag)

    db.commit()
    db.refresh(note)

    return _note_to_response(note)


# PUBLIC_INTERFACE
@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a note",
    description="Soft-delete a note by setting is_deleted=true and recording deleted_at timestamp.",
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "Note not found"},
    },
)
def delete_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Soft-delete a note (sets is_deleted flag and deleted_at timestamp).

    Args:
        note_id: The UUID of the note to delete.
        current_user: Authenticated user.
        db: Database session.
    """
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id,
        Note.is_deleted == False,
    ).first()

    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    note.is_deleted = True
    note.deleted_at = datetime.now(timezone.utc)
    note.updated_at = datetime.now(timezone.utc)
    db.commit()
