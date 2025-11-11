from typing import Dict, List, Optional, Set, Tuple
import copy
from tree_sitter import Node

from memory.utils.value import Value, ValueLabel
from utility.errors import RAAnalysisError

# Type aliases for improved readability
Scope = Tuple[int, int]
IfStatement = Tuple[int, int, str, Scope, Scope]
LoopStatement = Tuple[int, int, str, int, int]


class Function:
    """Represents a user-defined function or method with its analysis information.

    This class stores and manages information about a function including its basic metadata,
    AST nodes, parameters, return values, arguments, and control flow structures.
    """

    def __init__(
        self,
        function_id: int,
        function_name: str,
        function_code: str,
        start_line_number: int,
        end_line_number: int,
        function_node: Node,
        file_path: str,
    ) -> None:
        """Initialize a Function object with basic metadata and analysis structures.

        Args:
            function_id: Unique identifier for the function
            function_name: Name of the function
            function_code: Source code of the function
            start_line_number: First line number in source file
            end_line_number: Last line number in source file
            function_node: Root AST node of the function
            file_path: Path to source file containing the function
        """
        # Basic function metadata
        self.function_id = function_id
        self.function_name = function_name
        self.function_code = function_code
        self.start_line_number = start_line_number
        self.end_line_number = end_line_number
        self.file_path = file_path
        self.lined_code = self.attach_relative_line_number()
        self.parse_tree_root_node = function_node

        # Call site tracking
        self.function_call_site_nodes: Dict[int, Tuple[Node, str, int, int]] = {}
        self.api_call_site_nodes: Dict[int, Tuple[Node, str, int, int]] = {}
        self.all_call_site_nodes: Dict[int, Tuple[Node, str, int, int]] = {}

        # Function parameters and return values
        self._paras: Set[Value] = set()
        self._retvals: Set[Value] = set()

        # Arguments and output values at call sites
        self._args: Dict[int, Set[Value]] = {}
        self._outvals: Dict[int, Value] = {}

        # Control flow structures
        self.if_statements: Dict[Scope, IfStatement] = {}
        self.loop_statements: Dict[Scope, LoopStatement] = {}

    def add_para(self, para: Value) -> None:
        """Add a parameter to the function.

        Args:
            para: Parameter value to add
        """
        self._paras.add(para)

    def paras(self, para_label: Optional[ValueLabel] = None) -> Set[Value]:
        """Get the function's parameters, optionally filtered by label.

        Args:
            para_label: Optional label to filter parameters by

        Returns:
            Set of parameter Values matching the label, or all parameters if no label
        """
        if para_label is None:
            return copy.deepcopy(self._paras)

        assert para_label.is_para(), "para_label must be a parameter label"
        return {p for p in self._paras if p.label == para_label}

    def add_retval(self, retval: Value) -> None:
        """Add a return value to the function.

        Args:
            retval: Return value to add
        """
        self._retvals.add(retval)

    def retvals(self) -> Set[Value]:
        """Get all return values of the function.

        Returns:
            Set of all return Values
        """
        return copy.deepcopy(self._retvals)

    def add_arg(self, call_site_id: int, arg: Value) -> None:
        """Add an argument at a call site.

        Args:
            call_site_id: ID of the call site
            arg: Argument value to add
        """
        if call_site_id not in self._args:
            self._args[call_site_id] = set()
        self._args[call_site_id].add(arg)

    def args(
        self,
        line_number: Optional[int] = None,
        function_name: Optional[str] = None,
        index: Optional[int] = None,
        arg_label: Optional[ValueLabel] = None,
        call_site_id: Optional[int] = None,
    ) -> Set[Value]:
        """Get arguments matching the specified criteria.

        Args:
            line_number: Optional line number in function to filter by
            function_name: Optional callee function name to filter by
            index: Optional argument index to filter by
            arg_label: Optional argument label to filter by
            call_site_id: Optional call site ID to filter by

        Returns:
            Set of argument Values matching all specified criteria
        """
        target_args: Set[Value] = set()
        matching_call_sites = []

        # Find matching call sites
        for site_id, (
            node,
            callee_name,
            start_line,
            end_line,
        ) in self.all_call_site_nodes.items():
            if (
                (function_name is None or callee_name == function_name)
                and (line_number is None or start_line <= line_number <= end_line)
                and (call_site_id is None or site_id == call_site_id)
            ):
                matching_call_sites.append(site_id)

        # Collect matching arguments
        for site_id in matching_call_sites:
            if site_id not in self._args:
                continue
            for arg in self._args[site_id]:
                if (
                    (line_number is None or arg.line_number_in_function == line_number)
                    and (index is None or arg.index == index)
                    and (arg_label is None or arg.label == arg_label)
                ):
                    target_args.add(arg)

        return copy.deepcopy(target_args)

    def add_outval(self, call_site_id: int, outval: Value) -> None:
        """Add an output value at a call site.

        Args:
            call_site_id: ID of the call site
            outval: Output value to add
        """
        self._outvals[call_site_id] = outval

    def outval(self, call_site_id: int) -> Optional[Value]:
        """Get the output value at a specific call site.

        Args:
            call_site_id: ID of the call site

        Returns:
            Output Value if found, None otherwise
        """
        return copy.deepcopy(self._outvals.get(call_site_id))

    def outvals(
        self, line_number: Optional[int] = None, function_name: Optional[str] = None
    ) -> Set[Value]:
        """Get output values matching the specified criteria.

        Args:
            line_number: Optional line number to filter by
            function_name: Optional function name to filter by

        Returns:
            Set of output Values matching the criteria
        """
        target_outvals = set()
        matching_call_sites = []

        for site_id, (
            node,
            callee_name,
            start_line,
            end_line,
        ) in self.all_call_site_nodes.items():
            if (function_name is None or callee_name == function_name) and (
                line_number is None or start_line <= line_number <= end_line
            ):
                matching_call_sites.append(site_id)

        for site_id in matching_call_sites:
            if site_id in self._outvals:
                target_outvals.add(self._outvals[site_id])

        return copy.deepcopy(target_outvals)

    def get_call_site_id(self, node: Node) -> int:
        """Get the call site ID for a given AST node.

        Args:
            node: AST node to look up

        Returns:
            Call site ID if found, -1 otherwise
        """
        for site_id, (site_node, _, _, _) in self.all_call_site_nodes.items():
            if site_node == node:
                return site_id
        return -1

    def file_line2function_line(self, file_line: int) -> int:
        """Convert file line number to function-relative line number.

        Args:
            file_line: Line number in source file

        Returns:
            Line number relative to function start
        """
        return file_line - self.start_line_number + 1

    def attach_relative_line_number(self) -> str:
        """Generate function code with relative line numbers.

        Returns:
            Function code with line numbers starting from 1
        """
        lined_code = ""
        function_content = "1. " + self.function_code
        line_no = 2

        for ch in function_content:
            if ch == "\n":
                lined_code += f"\n{line_no}. "
                line_no += 1
            else:
                lined_code += ch

        return lined_code

    def attach_absolute_line_number(self) -> str:
        """Generate function code with absolute file line numbers.

        Returns:
            Function code with actual file line numbers
        """
        lined_code = ""
        function_content = f"{self.start_line_number}. " + self.function_code
        line_no = self.start_line_number + 1

        for ch in function_content:
            if ch == "\n":
                lined_code += f"\n{line_no}. "
                line_no += 1
            else:
                lined_code += ch

        return lined_code

    def __hash__(self) -> int:
        """Generate hash based on function identity.

        Returns:
            Hash of function's identifying attributes
        """
        return hash(
            (
                self.function_name,
                self.function_code,
                self.file_path,
                self.start_line_number,
                self.end_line_number,
            )
        )

    def __str__(self) -> str:
        """Generate string representation of function.

        Returns:
            String with function name and location
        """
        return f"Function {self.function_name} at {self.file_path}:{self.start_line_number}"

    def to_dict(self) -> dict:
        """Convert Function object to dictionary representation.

        Returns:
            Dictionary containing function metadata and analysis data
        """
        return {
            "function_id": self.function_id,
            "function_name": self.function_name,
            "function_code": self.function_code,
            "start_line_number": self.start_line_number,
            "end_line_number": self.end_line_number,
            "file_path": self.file_path,
            "paras": [value.to_dict() for value in self._paras],
            "retvals": [value.to_dict() for value in self._retvals],
            "args": {
                str(site_id): [arg.to_dict() for arg in args]
                for site_id, args in self._args.items()
            },
            "outvals": {
                str(site_id): value.to_dict()
                for site_id, value in self._outvals.items()
            },
        }
