import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Float, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


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
    corpuses: Mapped[list["Corpus"]] = relationship(
        "Corpus", back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
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
    user: Mapped[User] = relationship("User", back_populates="corpuses", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="corpus", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    filename: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    corpus_id: Mapped[str] = mapped_column(
        String, ForeignKey("corpuses.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    corpus: Mapped[Corpus] = relationship("Corpus", back_populates="documents", cascade="all, delete-orphan")
    user: Mapped[User] = relationship("User", back_populates="documents", cascade="all, delete-orphan")
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
    idf_score: Mapped[float | None] = mapped_column(Float)
    tfidf_score: Mapped[float | None] = mapped_column(Float)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id"), nullable=False
    )

    # Relationships
    document: Mapped[Document] = relationship(
        "Document", back_populates="word_frequencies", cascade="all, delete-orphan"
    )
