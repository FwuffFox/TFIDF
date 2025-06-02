from sqlalchemy import Column, String, Text
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class Document(Base):
    __tablename__ = 'documents'
    id = Column(String, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    hash = Column(String, unique=True, index=True, nullable=False)
