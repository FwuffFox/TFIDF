from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    corpuses = relationship("Corpus", back_populates="user")

class Corpus(Base):
    __tablename__ = 'corpuses'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="corpuses")
    documents = relationship("Document", back_populates="corpus")

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255))
    text = Column(Text, nullable=False)
    hash = Column(String, unique=True, index=True, nullable=False)
    corpus_id = Column(String, ForeignKey('corpuses.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    corpus = relationship("Corpus", back_populates="documents")
    word_frequencies = relationship("WordFrequency", back_populates="document")

class WordFrequency(Base):
    __tablename__ = 'word_frequencies'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    word = Column(String(100), nullable=False, index=True)
    frequency = Column(Integer, nullable=False)
    tf_score = Column(Float)
    idf_score = Column(Float) 
    tfidf_score = Column(Float)
    document_id = Column(String, ForeignKey('documents.id'), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="word_frequencies")
