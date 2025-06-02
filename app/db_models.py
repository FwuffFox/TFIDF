from sqlalchemy import Column, String, Text, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Document(Base):
    __tablename__ = 'documents'
    id = Column(String, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    hash = Column(String, unique=True, index=True, nullable=False)

Index('ix_documents_hash', Document.hash, unique=True)
