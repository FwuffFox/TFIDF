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
from app.utils.token_manager import (BLACKLIST_KEY_PREFIX,
                                     USER_TOKEN_KEY_PREFIX, TokenManager)

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
    current_time = datetime.now(timezone.utc)
    expires_delta = current_time + timedelta(minutes=int(expire_time))

    # Add expiration time
    to_encode.update({"exp": expires_delta})

    # Add issued-at time for token invalidation checks
    to_encode.update({"iat": current_time.timestamp()})

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

        # Check if all tokens for this user have been invalidated
        user_invalidation_key = f"{USER_TOKEN_KEY_PREFIX}{user_name}:invalidated_before"
        invalidated_timestamp = await token_manager.cache_storage.get(
            user_invalidation_key
        )

        if invalidated_timestamp:
            # Convert to float for comparison
            invalidated_time = float(invalidated_timestamp)
            token_created_time = payload.get("iat", 0)

            # If token was created before invalidation, reject it
            if token_created_time and token_created_time < invalidated_time:
                raise credentials_exception

    except jwt.PyJWTError:
        raise credentials_exception

    user = await user_repo.get_by_username(user_name)
    if user is None:
        raise credentials_exception
    return user


AuthenticatedUser = Annotated[User, Depends(get_current_user)]
