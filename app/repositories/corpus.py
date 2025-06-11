from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Corpus


class CorpusRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, corpus_id: str) -> Optional[Corpus]:
        """
        Retrieve a corpus by its ID.

        Args:
            corpus_id (str): The ID of the corpus to retrieve.

        Returns:
            Optional[Corpus]: The Corpus object if found, otherwise None.
        """
        result = await self.session.execute(
            select(Corpus).where(Corpus.id == corpus_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Corpus]:
        """
        Retrieve a corpus by its name.
        Args:
            name (str): The name of the corpus to retrieve.

        Returns:
            Optional[Corpus]: The Corpus object if found, otherwise None.
        """
        result = await self.session.execute(select(Corpus).where(Corpus.name == name))
        return result.scalar_one_or_none()

    async def get_by_user(
        self, user_id, offset: int = 0, limit: int = 50
    ) -> Sequence[Corpus]:
        """
        Retrieve corpuses associated with a specific user.

        Args:
            user_id (str): The ID of the user to filter corpuses by.
            offset (int): The number of records to skip (for pagination).
            limit (int): The maximum number of records to return.

        Returns:
            Sequence[Corpus]: A sequence of Corpus objects associated with the specified user.
        """
        result = await self.session.execute(
            select(Corpus).where(Corpus.user_id == user_id).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def create(self, name: str, user_id: str):
        corpus = Corpus(name=name, user_id=user_id)
        self.session.add(corpus)
        await self.session.commit()
        await self.session.refresh(corpus)
        return corpus

    async def delete(self, corpus_id: str):
        corpus = await self.get(corpus_id)
        if corpus:
            await self.session.delete(corpus)
            await self.session.commit()
        return corpus
