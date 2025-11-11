from abc import ABC, abstractmethod
from typing import Dict
from memory.IR.IR import IR


class State(ABC):
    """Abstract base class for scan state tracking.

    This class serves as the base for various state tracking classes used during
    code analysis scans. Subclasses implement specific state tracking functionality
    for different types of scans.
    """

    def __init__(self) -> None:
        """Initialize an empty state object."""
        pass
