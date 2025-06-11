import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.db.models import User
from app.dependencies import get_token_manager, get_user_repository
from app.repositories.user import UserRepository
from app.utils.token_manager import TokenManager

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")


def hash_password(password: str) -> str:
    """
    Hash a password using a secure hashing algorithm.
    """
    return pwd_context.hash(password)


def check_password(password: str, hashed: str) -> bool:
    """
    Check if the provided password matches the hashed password.
    """
    return pwd_context.verify(password, hashed)


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token with the given data.
    """
    to_encode = data.copy()
    expire_time = os.getenv("AUTH_EXPIRE_MINUTES", "60")
    expires_delta = datetime.now(timezone.utc) + timedelta(minutes=int(expire_time))
    to_encode.update({"exp": expires_delta})
    encoded_jwt = jwt.encode(
        to_encode,
        os.getenv("AUTH_JWT_SECRET"),
        algorithm=os.getenv("AUTH_ALGORITHM", "HS256"),
    )
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: UserRepository = Depends(get_user_repository),
    token_manager: TokenManager = Depends(get_token_manager),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check if token is blacklisted
    if await token_manager.is_token_blacklisted(token):
        raise credentials_exception
        
    try:
        payload = jwt.decode(
            token,
            os.getenv("AUTH_JWT_SECRET"),
            algorithms=[os.getenv("AUTH_ALGORITHM", "HS256")],
        )
        user_name: str = payload.get("sub")
        if user_name is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = await user_repo.get_by_username(user_name)
    if user is None:
        raise credentials_exception
    return user


AuthenticatedUser = Annotated[User, Depends(get_current_user)]
