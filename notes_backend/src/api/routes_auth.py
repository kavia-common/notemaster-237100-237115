"""
Authentication routes for user registration and login.
Provides JWT-based authentication for the NoteMaster API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.api.database import get_db
from src.api.models import User
from src.api.schemas import UserRegister, UserLogin, TokenResponse, UserResponse
from src.api.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# PUBLIC_INTERFACE
@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with username, email, and password. Returns a JWT token.",
    responses={
        409: {"description": "Username or email already exists"},
    },
)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Args:
        data: Registration data including username, email, and password.
        db: Database session.

    Returns:
        JWT access token and user details.
    """
    # Check for existing username or email
    existing = db.query(User).filter(
        or_(User.username == data.username, User.email == data.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    # Create new user
    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate JWT token
    token = create_access_token(str(user.id), user.username)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# PUBLIC_INTERFACE
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with username and password",
    description="Authenticate with username/email and password. Returns a JWT token.",
    responses={
        401: {"description": "Invalid credentials"},
    },
)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """
    Login with username/email and password.

    Args:
        data: Login data with username and password.
        db: Database session.

    Returns:
        JWT access token and user details.
    """
    # Look up user by username or email
    user = db.query(User).filter(
        or_(User.username == data.username, User.email == data.username)
    ).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Generate JWT token
    token = create_access_token(str(user.id), user.username)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# PUBLIC_INTERFACE
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the authenticated user's profile information.",
)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.

    Args:
        current_user: The authenticated user (injected by dependency).

    Returns:
        User profile data.
    """
    return UserResponse.model_validate(current_user)
