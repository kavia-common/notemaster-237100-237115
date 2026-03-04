"""
Sync routes for offline-first note synchronization.
Provides push (client -> server) and pull (server -> client) endpoints.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.models import Note, NoteTag, Tag, SyncLog, User
from src.api.schemas import (
    SyncPushRequest, SyncPushResponse, SyncPullResponse,
    NoteResponse, TagResponse,
)
from src.api.auth import get_current_user

router = APIRouter(prefix="/sync", tags=["Sync"])


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
@router.post(
    "/push",
    response_model=SyncPushResponse,
    summary="Push notes from client to server",
    description=(
        "Push local notes to the server for synchronization. "
        "Creates new notes or updates existing ones based on local_id matching. "
        "Uses last-write-wins conflict resolution based on updated_at timestamp."
    ),
    responses={
        401: {"description": "Authentication required"},
    },
)
def sync_push(
    data: SyncPushRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Push notes from client to server.

    For each note in the request:
    - If a note with matching local_id exists, update it (last-write-wins).
    - If no matching note exists, create it.
    - Tags are resolved by name and created if they don't exist.

    Args:
        data: Sync push request with notes to push.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Summary of synced notes count and any errors.
    """
    synced_count = 0
    errors = []

    for item in data.notes:
        try:
            # Look for existing note by local_id
            existing_note = db.query(Note).filter(
                Note.user_id == current_user.id,
                Note.local_id == item.local_id,
            ).first()

            if existing_note:
                # Last-write-wins: only update if client version is newer
                if item.updated_at > existing_note.updated_at:
                    existing_note.title = item.title
                    existing_note.content = item.content
                    existing_note.content_type = item.content_type
                    existing_note.is_pinned = item.is_pinned
                    existing_note.is_archived = item.is_archived
                    existing_note.is_deleted = item.is_deleted
                    existing_note.updated_at = item.updated_at

                    if item.is_deleted:
                        existing_note.deleted_at = datetime.now(timezone.utc)

                    # Update tags
                    _sync_tags(db, existing_note, item.tag_names, current_user)

                    # Log sync action
                    _log_sync(db, current_user.id, "update", "note", existing_note.id, item.updated_at)

                synced_count += 1
            else:
                # Create new note
                note = Note(
                    user_id=current_user.id,
                    title=item.title,
                    content=item.content,
                    content_type=item.content_type,
                    is_pinned=item.is_pinned,
                    is_archived=item.is_archived,
                    is_deleted=item.is_deleted,
                    local_id=item.local_id,
                    created_at=item.updated_at,
                    updated_at=item.updated_at,
                )
                if item.is_deleted:
                    note.deleted_at = datetime.now(timezone.utc)

                db.add(note)
                db.flush()  # Get note.id

                # Attach tags
                _sync_tags(db, note, item.tag_names, current_user)

                # Log sync action
                _log_sync(db, current_user.id, "create", "note", note.id, item.updated_at)

                synced_count += 1

        except Exception as e:
            errors.append(f"Error syncing note '{item.local_id}': {str(e)}")

    db.commit()

    return SyncPushResponse(
        synced_count=synced_count,
        errors=errors,
        server_timestamp=datetime.now(timezone.utc),
    )


# PUBLIC_INTERFACE
@router.get(
    "/pull",
    response_model=SyncPullResponse,
    summary="Pull notes from server to client",
    description=(
        "Pull notes updated since the given timestamp from the server. "
        "Used by the client to download changes made on other devices."
    ),
    responses={
        401: {"description": "Authentication required"},
    },
)
def sync_pull(
    since: Optional[datetime] = Query(None, description="Pull notes updated after this timestamp (ISO 8601)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Pull notes updated since a given timestamp.

    Args:
        since: Optional timestamp; only notes updated after this time are returned.
               If None, all notes are returned.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of updated notes and current server timestamp.
    """
    query = db.query(Note).filter(Note.user_id == current_user.id)

    if since:
        query = query.filter(Note.updated_at > since)

    notes = query.order_by(Note.updated_at.desc()).all()

    return SyncPullResponse(
        notes=[_note_to_response(n) for n in notes],
        server_timestamp=datetime.now(timezone.utc),
    )


def _sync_tags(db: Session, note: Note, tag_names: list, user: User):
    """
    Sync tags for a note during push. Creates tags that don't exist.
    Removes old note_tag associations and creates new ones.
    """
    if tag_names is None:
        return

    # Remove existing associations
    db.query(NoteTag).filter(NoteTag.note_id == note.id).delete()

    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        # Find or create tag
        tag = db.query(Tag).filter(Tag.user_id == user.id, Tag.name == name).first()
        if not tag:
            tag = Tag(user_id=user.id, name=name)
            db.add(tag)
            db.flush()

        note_tag = NoteTag(note_id=note.id, tag_id=tag.id)
        db.add(note_tag)


def _log_sync(db: Session, user_id, action: str, entity_type: str, entity_id, client_timestamp):
    """Record a sync log entry."""
    log = SyncLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        sync_status="completed",
        client_timestamp=client_timestamp,
        server_timestamp=datetime.now(timezone.utc),
    )
    db.add(log)
