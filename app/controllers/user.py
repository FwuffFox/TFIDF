# Контроллер для работы с пользователями
import asyncio
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.controllers.utils.responses import response401
from app.dependencies import (get_document_repository, get_storage_service,
                              get_token_manager, get_user_repository)
from app.repositories.document import DocumentRepository
from app.repositories.user import UserRepository
from app.utils.auth import (AuthenticatedUser, create_access_token,
                            oauth2_scheme)
from app.utils.storage import FileStorage
from app.utils.token_manager import TokenManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])


class LoginDTO(BaseModel):
    username: str
    password: str


class RegisterDTO(LoginDTO):
    email: str


class UserDTO(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime


class ChangePasswordDTO(BaseModel):
    old_password: str
    new_password: str


@router.post(
    "/register",
    summary="Register new user",
    description="Creates a new user account with the provided username, password, and email.",
    responses={
        200: {
            "description": "User successfully registered",
            "content": {"application/json": {"example": {"status": "registered"}}},
        },
        400: {
            "description": "Username or email already exists",
            "content": {
                "application/json": {"example": {"detail": "Username already exists"}}
            },
        },
    },
)
async def register(
    dto: RegisterDTO, repo: UserRepository = Depends(get_user_repository)
):
    """
    Register a new user in the system.

    Args:
        dto (RegisterDTO): The user registration data containing username, password, and email.
        repo (UserRepository, optional): User repository dependency.

    Returns:
        dict: A status message indicating successful registration.

    Raises:
        HTTPException: 400 error if username or email already exists.
    """
    if await repo.get_by_username(dto.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    if await repo.get_by_email(dto.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    logger.info(f"Registering new user {dto.username}")
    await repo.create(dto.username, dto.password, dto.email)

    return {"status": "registered"}


@router.post(
    "/login",
    summary="User login",
    description="Authenticates a user and returns a JWT access token for API access.",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                    }
                }
            },
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid username or password"}
                }
            },
        },
    },
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    repo: UserRepository = Depends(get_user_repository),
):
    """
    Authenticate a user and provide an access token.

    Args:
        form_data (OAuth2PasswordRequestForm): Form containing username and password.
        repo (UserRepository, optional): User repository dependency.

    Returns:
        dict: JWT access token and token type for authentication.

    Raises:
        HTTPException: 401 error if username or password is invalid.
    """
    user = await repo.get_by_username(form_data.username)
    if not user or not await repo.check_password(user, form_data.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserDTO,
    summary="Get current user",
    description="Returns the profile information for the currently authenticated user.",
    responses={
        200: {
            "description": "Current user details",
            "model": UserDTO,
        },
        401: response401,
    },
)
async def get_current_user(user: AuthenticatedUser):
    """
    Get the current authenticated user's information.

    Args:
        user (AuthenticatedUser): The current authenticated user (injected via dependency).

    Returns:
        UserDTO: User information including id, username, email, and creation date.
    """
    return user


@router.post(
    "/logout",
    summary="User logout",
    description="Logs out the current user by invalidating their access token.",
    responses={
        200: {
            "description": "Successfully logged out",
            "content": {
                "application/json": {"example": {"status": "logged out successfully"}}
            },
        },
        400: {
            "description": "Logout failed",
            "content": {"application/json": {"example": {"detail": "Logout failed"}}},
        },
        401: response401,
    },
)
async def logout(
    user: AuthenticatedUser,
    token: str = Depends(oauth2_scheme),
    token_manager: TokenManager = Depends(get_token_manager),
):
    """
    Logout endpoint that blacklists the current token.

    This effectively logs out the user by invalidating their current access token.
    The token will be added to a blacklist and won't be usable for authentication anymore.

    Args:
        user (AuthenticatedUser): The current authenticated user.
        token (str): The current JWT token to be blacklisted.
        token_manager (TokenManager): Service to manage token blacklisting.

    Returns:
        dict: A status message indicating successful logout.

    Raises:
        HTTPException: 400 error if logout operation failed.
    """
    success = await token_manager.blacklist_token(token)
    if success:
        return {"status": "logged out successfully"}
    else:
        raise HTTPException(status_code=400, detail="Logout failed")


@router.patch(
    "/",
    summary="Change password",
    description="Changes the user's password and invalidates all existing sessions.",
    responses={
        200: {
            "description": "Password changed successfully",
            "content": {
                "application/json": {
                    "example": {"status": "password changed, all sessions invalidated"}
                }
            },
        },
        401: response401,
    },
)
async def change_password(
    user: AuthenticatedUser,
    data: ChangePasswordDTO,
    token: str = Depends(oauth2_scheme),
    repo: UserRepository = Depends(get_user_repository),
    token_manager: TokenManager = Depends(get_token_manager),
):
    """
    Change the current user's password.

    This endpoint allows users to change their password. After changing the password,
    all existing tokens for the user are invalidated for security purposes.

    Args:
        user (AuthenticatedUser): The current authenticated user.
        data (ChangePasswordDTO): Old and new password information.
        token (str): The current JWT token.
        repo (UserRepository): User repository for password operations.
        token_manager (TokenManager): Service to manage token blacklisting.

    Returns:
        dict: A status message indicating successful password change.

    Raises:
        HTTPException: 401 error if the old password is invalid.
    """
    if not await repo.check_password(user, data.old_password):
        raise HTTPException(status_code=401, detail="Invalid old password")

    await repo.change_password(user, data.new_password)

    logger.info("Password changed successfully for user: %s", user.username)
    logger.info("Invalidating all sessions for user: %s", user.username)
    await token_manager.blacklist_all_user_tokens(user.username)
    await token_manager.blacklist_token(token)

    return {"status": "password changed, all sessions invalidated"}


@router.delete(
    "/",
    summary="Delete user account",
    description="Permanently deletes the user account and all associated data. Requires password confirmation.",
    responses={
        200: {
            "description": "User deleted successfully",
            "content": {
                "application/json": {
                    "example": {"status": "user deleted, all sessions invalidated"}
                }
            },
        },
        401: response401,
    },
)
async def delete_user(
    user: AuthenticatedUser,
    password: str,
    user_repo: UserRepository = Depends(get_user_repository),
    doc_repo: DocumentRepository = Depends(get_document_repository),
    storage: FileStorage = Depends(get_storage_service),
    token_manager: TokenManager = Depends(get_token_manager),
):
    """
    Delete the current user's account.

    This endpoint permanently deletes the user account and all associated data.
    It requires password confirmation for security. User documents are also removed
    from storage, and all authentication tokens are invalidated.

    Args:
        user (AuthenticatedUser): The current authenticated user.
        password (str): The user's password for verification.
        user_repo (UserRepository): Repository for user operations.
        doc_repo (DocumentRepository): Repository for document operations.
        storage (FileStorage): Service for file storage operations.
        token_manager (TokenManager): Service to manage token blacklisting.

    Returns:
        dict: A status message indicating successful account deletion.

    Raises:
        HTTPException: 401 error if the provided password is invalid.
    """
    logger.info(f"Account deletion requested for user: {user.username}")

    if not await user_repo.check_password(user, password):
        logger.warning(
            f"Failed account deletion attempt for user: {user.username} - Invalid password"
        )
        raise HTTPException(status_code=401, detail="Invalid password")

    logger.info(
        f"Password verified for user: {user.username}, proceeding with account deletion"
    )

    logger.info(f"Blacklisting all tokens for user: {user.username}")
    await token_manager.blacklist_all_user_tokens(user.username)

    async def background_task():
        try:
            logger.info(f"Retrieving documents for user: {user.id}")
            user_documents = await doc_repo.get_by_user(user.id)
            logger.info(
                f"Found {len(user_documents)} documents to delete for user: {user.username}"
            )

            delete_file_tasks = [
                storage.delete_file_by_path(doc.location) for doc in user_documents
            ]
            logger.info(
                f"Deleting user account and associated documents for user: {user.username}"
            )
            tasks = delete_file_tasks + [user_repo.delete(user.id)]

            await asyncio.gather(*tasks)
            logger.info(
                f"Successfully completed account deletion for user: {user.username}"
            )
        except Exception as e:
            logger.error(
                f"Error during account deletion for user {user.username}: {str(e)}"
            )
            # We can't raise an HTTP exception here as this is a background task

    asyncio.create_task(background_task())
    logger.info(f"Account deletion process initiated for user: {user.username}")
    return {"status": "user deleted, all sessions invalidated"}
