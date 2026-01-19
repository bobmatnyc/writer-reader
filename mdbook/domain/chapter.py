from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import date

@dataclass
class ChapterMetadata:
    title: str
    number: Optional[int] = None
    author: Optional[str] = None
    date: Optional[date] = None
    draft: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Chapter:
    file_path: Path
    metadata: ChapterMetadata
    is_intro: bool = False

    @property
    def title(self) -> str:
        return self.metadata.title

    @property
    def number(self) -> Optional[int]:
        return self.metadata.number
