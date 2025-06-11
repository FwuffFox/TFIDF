# Контроллер для работы с пользователями
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.dependencies import get_token_manager, get_user_repository
from app.repositories.user import UserRepository
from app.utils.auth import (AuthenticatedUser, create_access_token,
                            oauth2_scheme)
from app.utils.token_manager import TokenManager

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


@router.post("/register")
async def register(
    dto: RegisterDTO, repo: UserRepository = Depends(get_user_repository)
):
    if await repo.get_by_username(dto.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    if await repo.get_by_email(dto.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    await repo.create(dto.username, dto.password, dto.email)

    return {"status": "registered"}


@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    repo: UserRepository = Depends(get_user_repository),
):
    user = await repo.get_by_username(form_data.username)
    if not user or not await repo.check_password(user, form_data.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserDTO)
async def get_current_user(user: AuthenticatedUser):
    return user


@router.post("/logout")
async def logout(
    user: AuthenticatedUser,
    token: str = Depends(oauth2_scheme),
    token_manager: TokenManager = Depends(get_token_manager),
):
    """
    Logout endpoint that blacklists the current token.

    This effectively logs out the user by invalidating their current access token.
    The token will be added to a blacklist and won't be usable for authentication anymore.
    """
    success = await token_manager.blacklist_token(token)
    if success:
        return {"status": "logged out successfully"}
    else:
        raise HTTPException(status_code=400, detail="Logout failed")


@router.patch("/")
async def change_password(
    user: AuthenticatedUser,
    data: ChangePasswordDTO,
    token: str = Depends(oauth2_scheme),
    repo: UserRepository = Depends(get_user_repository),
    token_manager: TokenManager = Depends(get_token_manager)
):
    if not await repo.check_password(user, data.old_password):
        raise HTTPException(status_code=401, detail="Invalid old password")
    
    await repo.change_password(user, data.new_password)
    
    # Blacklist all existing tokens for this user
    await token_manager.blacklist_all_user_tokens(user.username)
    
    # Additionally blacklist the current token to force immediate logout
    await token_manager.blacklist_token(token)
    
    return {"status": "password changed, all sessions invalidated"}


@router.delete("/")
async def delete_user(
    user_id: str, repo: UserRepository = Depends(get_user_repository)
):
    # TODO: реализовать удаление пользователя
    return {"status": "user deleted"}
