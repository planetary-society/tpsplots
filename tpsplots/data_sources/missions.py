from pathlib import Path
from typing import ClassVar

from .nasa_budget_data_source import NASABudget


class Missions(NASABudget):
    
    CSV_URL = ("https://docs.google.com/spreadsheets/d/"
               "1-8GAxFqBUStyUUK7Dv25SnfSX_y2PxulUet2fsJw69Y/"
               "export?format=csv&gid=131059667")
    
    COLUMNS: ClassVar[list[str]] = [
        "Mission",
        "Status",
        "Project Type",
        "Nation",
        "NASA Led?",
        "LCC",
        "Formulation Start",
        "Launch Date",
    ]
    MONETARY_COLUMNS: ClassVar[list[str]] = ["LCC"]
    
    def __init__(self, *, cache_dir: Path | None = None) -> None:
        super().__init__(self.CSV_URL, cache_dir=cache_dir)
