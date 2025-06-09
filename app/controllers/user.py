# Контроллер для работы с пользователями
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.dependencies import get_user_repository
from app.repositories.user import UserRepository
from app.utils.auth import AuthenticatedUser, create_access_token

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


@router.get("/logout")
async def logout(user: AuthenticatedUser):
    # TODO: реализовать логаут
    return {"status": "logged out"}


@router.patch("/{user_id}")
async def change_password(
    user_id: str, new_password: str, repo: UserRepository = Depends(get_user_repository)
):
    # TODO: реализовать смену пароля
    return {"status": "password changed"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: str, repo: UserRepository = Depends(get_user_repository)
):
    # TODO: реализовать удаление пользователя
    return {"status": "user deleted"}
