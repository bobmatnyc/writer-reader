from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from datetime import date
from .chapter import Chapter

@dataclass
class BookMetadata:
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    language: str = "en"
    created: Optional[date] = None

@dataclass
class Book:
    root_path: Path
    metadata: BookMetadata
    chapters: List[Chapter] = field(default_factory=list)

    def get_chapter(self, number: int) -> Optional[Chapter]:
        for ch in self.chapters:
            if ch.number == number:
                return ch
        return None

    def get_intro(self) -> Optional[Chapter]:
        for ch in self.chapters:
            if ch.is_intro:
                return ch
        return None
