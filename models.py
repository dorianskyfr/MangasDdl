from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

class DownloadStatus(Enum):
    PENDING = "En attente"
    DOWNLOADING = "En cours"
    COMPLETED = "Terminé"
    FAILED = "Échec"
    PAUSED = "En pause"

@dataclass
class Manga:
    title: str
    url: str
    source: str
    cover_url: Optional[str] = None
    synopsis: Optional[str] = "Aucun synopsis disponible."
    genres: List[str] = field(default_factory=list)
    alt_titles: List[str] = field(default_factory=list)

@dataclass
class Chapter:
    title: str
    number: str
    url: str
    manga_title: str
    source: str

@dataclass
class Page:
    number: int
    url: str
    referer: Optional[str] = None

@dataclass
class DownloadJob:
    job_id: str
    manga_title: str
    chapter_number: str
    chapter_title: str
    chapter_url: str
    source: str
    total_pages: int = 0
    downloaded_pages: int = 0
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    speed: str = "0 Ko/s"
    error_message: Optional[str] = None
    save_path: str = ""
    export_format: str = "CBZ"  # Images, CBZ, PDF
    is_volume: bool = False
    volume_number: int = 0
    chapters_list: List[Chapter] = field(default_factory=list)
