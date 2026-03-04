"""
Tags CRUD routes for the NoteMaster API.
Provides endpoints for creating, listing, updating, and deleting tags.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.api.database import get_db
from src.api.models import Tag, User
from src.api.schemas import TagCreate, TagUpdate, TagResponse
from src.api.auth import get_current_user

router = APIRouter(prefix="/tags", tags=["Tags"])


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[TagResponse],
    summary="List all tags",
    description="List all tags for the authenticated user.",
    responses={
        401: {"description": "Authentication required"},
    },
)
def list_tags(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all tags belonging to the current user.

    Args:
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of tags.
    """
    tags = db.query(Tag).filter(Tag.user_id == current_user.id).order_by(Tag.name).all()
    return [TagResponse.model_validate(t) for t in tags]


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tag",
    description="Create a new tag for the authenticated user. Tag names are unique per user.",
    responses={
        401: {"description": "Authentication required"},
        409: {"description": "Tag with this name already exists"},
    },
)
def create_tag(
    data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new tag.

    Args:
        data: Tag creation data.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        The created tag.
    """
    # Check for duplicate tag name for this user
    existing = db.query(Tag).filter(
        Tag.user_id == current_user.id,
        Tag.name == data.name,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag with this name already exists",
        )

    tag = Tag(
        user_id=current_user.id,
        name=data.name,
        color=data.color,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)

    return TagResponse.model_validate(tag)


# PUBLIC_INTERFACE
@router.put(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Update a tag",
    description="Update an existing tag's name or color.",
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "Tag not found"},
        409: {"description": "Tag with this name already exists"},
    },
)
def update_tag(
    tag_id: UUID,
    data: TagUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing tag.

    Args:
        tag_id: The UUID of the tag to update.
        data: Fields to update.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        The updated tag.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    # Check for name conflict if name is being changed
    if data.name and data.name != tag.name:
        existing = db.query(Tag).filter(
            Tag.user_id == current_user.id,
            Tag.name == data.name,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tag with this name already exists",
            )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tag, field, value)

    db.commit()
    db.refresh(tag)

    return TagResponse.model_validate(tag)


# PUBLIC_INTERFACE
@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tag",
    description="Delete a tag. This also removes the tag from all associated notes.",
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "Tag not found"},
    },
)
def delete_tag(
    tag_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a tag (cascade removes note_tags associations).

    Args:
        tag_id: The UUID of the tag to delete.
        current_user: Authenticated user.
        db: Database session.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    db.delete(tag)
    db.commit()
