from pydantic import BaseModel
from typing import Optional, List, Dict

# -------------------------------
# Схемы для взаимодействия с БД
# -------------------------------

class ChunkSchema(BaseModel):
    id: Optional[int]
    part_number: Optional[str]
    #subpart: Optional[str]
    section_number: str
    text: str
    cross_references: Optional[List[str]]
    metadata: Optional[Dict]

    class Config:
        from_attributes = True


class ChunkCreateSchema(BaseModel):
    part_number: Optional[str]
    #subpart: Optional[str]
    section_number: str
    text: str
    cross_references: Optional[List[str]]
    metadata: Optional[Dict]


# -------------------------------
# Схема результата парсера
# -------------------------------

class ChunkData(BaseModel):
    part_number: Optional[str]
    #subpart: Optional[str]
    section_number: str
    text: str
    cross_references: List[str]