from __future__ import annotations

import datetime
import uuid
from typing import Optional

from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, String,
                        Table, Text)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


document_collection_association_table = Table(
    "document_collection_association_table",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("collection_id", ForeignKey("collections.id"), primary_key=True),
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
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.UTC)
    )

    # Relationships
    collections: Mapped[list[Collection]] = relationship(
        "Collection", back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.UTC)
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="collections")
    documents: Mapped[list[Document]] = relationship(
        secondary=document_collection_association_table, back_populates="collections"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.UTC)
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="documents")
    collections: Mapped[list[Collection]] = relationship(
        secondary=document_collection_association_table, back_populates="documents"
    )
    word_frequencies: Mapped[list[WordFrequency]] = relationship(
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
