from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


document_corpus_association_table = Table(
    "document_corpus_association_table",
    Base.metadata,
    Column("document_id", ForeignKey("document.id"), primary_key=True),
    Column("corpus_id", ForeignKey("corpus.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Bcrypted password
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    corpuses: Mapped[list[Corpus]] = relationship(
        "Corpus", back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )


class Corpus(Base):
    __tablename__ = "corpuses"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="corpuses")
    documents: Mapped[list[Document]] = relationship(
        secondary=document_corpus_association_table, back_populates="corpuses"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="documents")
    corpuses: Mapped[list[Corpus]] = relationship(
        secondary=document_corpus_association_table, back_populates="documents"
    )
    word_frequencies: Mapped[list["WordFrequency"]] = relationship(
        "WordFrequency", back_populates="document", cascade="all, delete-orphan"
    )


class WordFrequency(Base):
    __tablename__ = "word_frequencies"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    word: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    tf_score: Mapped[float | None] = mapped_column(Float)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id"), nullable=False
    )

    # Relationships
    document: Mapped[Document] = relationship(
        "Document", back_populates="word_frequencies"
    )
