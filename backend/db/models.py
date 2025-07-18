from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Структурные поля
    part_number = Column(String, nullable=True)
    subpart = Column(String, nullable=True)  # <-- добавляем сюда!
    section_number = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("chunks.id"), nullable=True)
    parent_section_number = Column(String, nullable=True)

    title = Column(String, nullable=True)
    text = Column(Text, nullable=False)

    # Поиск
    bm25_text = Column(TSVECTOR)
    embedding_vector = Column(Vector(1024))

    meta = Column(JSONB, nullable=True)

    # Связи
    parent = relationship("Chunk", remote_side=[id], backref="children")

    __table_args__ = (
        Index('ix_chunks_bm25_text', 'bm25_text', postgresql_using='gin'),
    )