from typing import Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, username: str, password: str, email: str):
        """
        Create a new user with the given username, password, and email.

        Password is passed unhashed, and should be hashed before storing.
        """
        from app.utils.auth import \
            hash_password  # Assuming you have a utility function to hash passwords

        password_hash = hash_password(password)
        user = User(username=username, password_hash=password_hash, email=email)
        self.session.add(user)
        await self.session.commit()
        return user

    async def check_password(self, user: User, password: str) -> bool:
        """
        Check if the provided password matches the stored password hash.
        """
        from app.utils.auth import check_password

        return check_password(password, user.password_hash)  # type: ignore
