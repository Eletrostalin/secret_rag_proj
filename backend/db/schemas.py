from pydantic import BaseModel
from typing import Optional, List, Dict

# -------------------------------
# Схема результата парсера
# -------------------------------

class ChunkData(BaseModel):
    part_number: Optional[str]
    #subpart: Optional[str]
    section_number: str
    #title: str
    text: str
    cross_references: List[str]