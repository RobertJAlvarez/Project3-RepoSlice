from typing import Dict, List, Tuple, Optional
import threading

from memory.state.state import State
from memory.utils.api import *
from memory.utils.function import Function
from memory.utils.value import Value
from llmtool.slicescan.intra_slicer import IntraSlicerInput
from memory.IR.IR import IR
from memory.IR.U6IR import U6IR


class SliceScanState(State):
    """State class for tracking program slicing progress and results."""

    def __init__(self) -> None:
        self._slicing_request_id: str = ""
        self._seed_function: Optional[Function] = None
        self._seed_value: Optional[Value] = None
        self._call_depth: int = 1
        self._is_backward: bool = True

        # Slicing results
        self._relevant_function_names_to_line_numbers: Dict[str, List[int]] = {}

        # TODO: Add your implementation here.
        # You can define any other attributes as you need.
        pass

    def initialize_slicescan_state(
        self,
        slicing_request_id: str,
        seed_function: Function,
        seed_value: Value,
        call_depth: int = 1,
        is_backward: bool = True,
    ) -> None:
        """Initialize the slicing state.

        Args:
            slicing_request_id: The ID of the slicing request
            seed_function: Function containing the slicing seeds
            seed_value: Seed value to start slicing from
            call_depth: Maximum call depth for interprocedural slicing
            is_backward: Whether to perform backward slicing
        """
        self._slicing_request_id = slicing_request_id
        self._seed_function = seed_function
        self._seed_value = seed_value
        self._call_depth = call_depth
        self._is_backward = is_backward

    def update_relevant_function_names_to_line_numbers(
        self, function_name: str, line_numbers: List[int]
    ) -> None:
        """Update the relevant function names to line numbers.

        Args:
            function_name: The name of the function
            line_numbers: The line numbers of the function
        """
        dedup_sorted = sorted(set(line_numbers))
        if function_name not in self._relevant_function_names_to_line_numbers:
            self._relevant_function_names_to_line_numbers[function_name] = dedup_sorted
        else:
            combined = (
                self._relevant_function_names_to_line_numbers[function_name]
                + line_numbers
            )
            self._relevant_function_names_to_line_numbers[function_name] = sorted(
                set(combined)
            )

    def to_dict(self) -> dict:
        """Convert state to dictionary representation.

        Returns:
            Dictionary containing slicing configuration and results
        """
        return {
            # TODO: Add your implementation here.
            # You can add any other information you need to record.
            # But we only check the key "relevant_function_names_to_line_numbers" to judge your implementation.
            "slicing_request_id": self._slicing_request_id,
            "relevant_function_names_to_line_numbers": self._relevant_function_names_to_line_numbers,
        }
