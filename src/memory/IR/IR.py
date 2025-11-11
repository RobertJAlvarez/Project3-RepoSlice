from abc import ABC, abstractmethod
from typing import Dict, Optional


class IR(ABC):
    """Abstract base class for intermediate representations used in code analysis."""

    def __init__(self, code_in_files: Dict[str, str]) -> None:
        self.code_in_files = code_in_files
