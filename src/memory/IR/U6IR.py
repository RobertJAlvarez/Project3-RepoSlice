import os
import json
import threading
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from memory.IR.IR import IR
from tree_sitter import Node
from memory.utils.function import Function
from memory.utils.api import API


class Parenthesis(Enum):
    LEFT_PAR = -1
    RIGHT_PAR = 1

    def __str__(self) -> str:
        return self.name


class ContextLabel:
    def __init__(
        self,
        file_name: str,
        line_number: int,
        function_id: int,
        parenthesis: Parenthesis,
    ):
        self.file_name = file_name
        self.line_number = line_number
        self.function_id = function_id
        self.parenthesis = parenthesis

    def __str__(self) -> str:
        return f"({self.file_name} {self.line_number} {self.function_id} {self.parenthesis})"


class U6IR(IR):
    """Intermediate Representation for U6 code analysis framework.

    This class encapsulates all analysis data extracted from source code, including:
    - Raw parsing results from tree-sitter AST analysis
    - Processed function and API metadata
    - Call graph relationships between functions and APIs
    - Thread-safe data structures for concurrent analysis

    The U6IR provides a centralized repository for all code analysis artifacts,
    enabling efficient storage, retrieval, and manipulation of analysis results.

    Attributes:
        Raw Parsing Data:
        - functionRawDataDic: Raw function AST nodes with metadata
        - functionNameToId: Function name to ID mappings
        - functionToFile: Function ID to file path mappings
        - fileContentDic: File content cache
        - glb_var_map: Global variable definitions

        Processed Analysis Objects:
        - function_env: Analyzed function objects
        - api_env: Analyzed API objects

        Call Graph Relationships:
        - function_caller_callee_map: Function-to-function call relationships
        - function_callee_caller_map: Reverse function call relationships
        - function_caller_api_callee_map: Function-to-API call relationships
        - api_callee_function_caller_map: Reverse API call relationships

        Thread Safety:
        - Various locks for concurrent access protection
    """

    def __init__(self, code_in_files: Dict[str, str]) -> None:
        """Initialize U6IR with source code and optional persistence directory.

        Args:
            code_in_files: Dictionary mapping file paths to their source code content
        """
        super().__init__(code_in_files)

        # ====================================================================
        # RAW PARSING DATA
        # Data structures populated during initial AST parsing phase
        # ====================================================================

        # Raw function metadata from tree-sitter parsing
        # Maps function_id -> (AST_node, function_name, start_line, end_line)
        self.functionRawDataDic: Dict[int, Tuple[Node, str, int, int]] = {}

        # Function name resolution mappings
        # Maps function_name -> set of function_ids (handles overloaded functions)
        self.functionNameToId: Dict[str, Set[int]] = {}

        # Function location mappings
        # Maps function_id -> file_path where function is defined
        self.functionToFile: Dict[int, str] = {}

        # File content cache for efficient access during analysis
        # Maps file_path -> file_content_string
        self.fileContentDic: Dict[str, str] = {}

        # Global variable and macro definitions
        # Maps variable/macro_name -> definition_string
        self.glb_var_map: Dict[str, str] = {}

        # ====================================================================
        # PROCESSED ANALYSIS OBJECTS
        # Rich objects created from raw parsing data with detailed metadata
        # ====================================================================

        # Comprehensive function analysis results
        # Maps function_id -> Function object (with parameters, return values, etc.)
        self.function_env: Dict[int, Function] = {}

        # Library API call analysis results
        # Maps api_id -> API object (with signatures, etc.)
        self.api_env: Dict[int, API] = {}

        # ====================================================================
        # CALL GRAPH RELATIONSHIPS
        # Inter-procedural analysis results capturing program control flow
        # ====================================================================

        # Function-to-Function Call Relationships (Forward)
        # Maps caller_function_id -> {call_site_id -> {callee_function_id, ...}}
        # Tracks which functions are called from each function and where
        self.function_caller_callee_map: Dict[int, Dict[int, Set[int]]] = {}

        # Function-to-Function Call Relationships (Reverse)
        # Maps callee_function_id -> {(call_site_id, caller_function_id), ...}
        # Enables efficient reverse lookup: "what calls this function?"
        self.function_callee_caller_map: Dict[int, Set[Tuple[int, int]]] = {}

        # Function-to-API Call Relationships (Forward)
        # Maps caller_function_id -> {call_site_id -> {api_id, ...}}
        # Tracks which APIs are called from each function
        self.function_caller_api_callee_map: Dict[int, Dict[int, Set[int]]] = {}

        # Function-to-API Call Relationships (Reverse)
        # Maps api_id -> {(call_site_id, caller_function_id), ...}
        # Enables efficient API usage analysis: "what uses this API?"
        self.api_callee_function_caller_map: Dict[int, Set[Tuple[int, int]]] = {}

        # ====================================================================
        # THREAD SAFETY MECHANISMS
        # Locks for protecting data structures during concurrent analysis
        # ====================================================================
        self.function_caller_callee_map_lock = threading.Lock()
        self.function_callee_caller_map_lock = threading.Lock()
        self.function_caller_api_callee_map_lock = threading.Lock()
        self.api_callee_function_caller_map_lock = threading.Lock()
        self.api_env_lock = threading.Lock()

    #################################################
    # Helper functions for caller/callee retrieval  #
    #################################################

    # Helper functions for callers
    def get_all_caller_functions(self, function: Function) -> List[Function]:
        """
        Get all functions that call the given function.

        Args:
            function: Function to analyze

        Returns:
            List of caller functions
        """
        callers = set()
        if function.function_id in self.function_callee_caller_map:
            for _, caller_id in self.function_callee_caller_map[function.function_id]:
                callers.add(self.function_env[caller_id])
        return list(callers)

    # Helper functions retrieving callees (user-defined functions)
    def get_all_callee_functions(self, function: Function) -> List[Function]:
        """
        Get all functions called by the given function.

        Args:
            function: Function to analyze

        Returns:
            List of called functions
        """
        function_callees = set()
        if function.function_id in self.function_caller_callee_map:
            for _, callee_ids in self.function_caller_callee_map[
                function.function_id
            ].items():
                for callee_id in callee_ids:
                    function_callees.add(self.function_env[callee_id])
        return list(function_callees)

    # Helper functions retrieving callees (library APIs)
    def get_all_callee_apis(self, function: Function) -> List[API]:
        """
        Get all APIs called by the given function.

        Args:
            function: Function to analyze

        Returns:
            List of called APIs
        """
        api_callees = []
        if function.function_id in self.function_caller_api_callee_map:
            for _, callee_api_ids in self.function_caller_api_callee_map[
                function.function_id
            ].items():
                for callee_api_id in callee_api_ids:
                    api_callees.append(self.api_env[callee_api_id])
        return api_callees

    # Helper functions retrieving callees (user-defined functions) by call site
    def get_callee_functions_by_callsite(
        self, function: Function, call_site_node: Node
    ) -> List[Function]:
        """
        Get all functions called by the given function at the given call site.
        """
        # First, search the call site id of call_site_node in the function
        call_site_id = -1
        # self.function_call_site_nodes: Dict[int, Tuple[Node, str, int, int]] = {}
        for node_id, (
            node,
            callee_name,
            start_line,
            end_line,
        ) in function.function_call_site_nodes.items():
            if node == call_site_node:
                call_site_id = node_id
                break

        if call_site_id == -1:
            return []

        # Second, search the callee ids in the function_caller_callee_map
        if function.function_id not in self.function_caller_callee_map:
            return []

        if call_site_id not in self.function_caller_callee_map[function.function_id]:
            return []

        callee_ids = self.function_caller_callee_map[function.function_id][call_site_id]
        return [self.function_env[callee_id] for callee_id in callee_ids]

    # Helper functions retrieving transitive callers (user-defined functions)
    def get_all_transitive_caller_functions(
        self, function: Function, max_depth=1000
    ) -> List[Function]:
        """
        Get all functions that transitively call the given function.

        Args:
            function: Function to analyze
            max_depth: Maximum call chain depth

        Returns:
            List of transitive caller functions
        """
        if max_depth == 0:
            return []
        if function.function_id not in self.function_callee_caller_map:
            return []

        caller_ids = []
        for _, caller_id in self.function_callee_caller_map[function.function_id]:
            caller_ids.append(caller_id)
        caller_functions = [self.function_env[caller_id] for caller_id in caller_ids]

        for caller_function in caller_functions:
            caller_functions.extend(
                self.get_all_transitive_caller_functions(caller_function, max_depth - 1)
            )
        caller_functions = list(
            {function.function_id: function for function in caller_functions}.values()
        )
        return caller_functions

    # Helper functions retrieving transitive callees (user-defined functions)
    def get_all_transitive_callee_functions(
        self, function: Function, max_depth=1000
    ) -> List[Function]:
        """
        Get all functions transitively called by the given function.

        Args:
            function: Function to analyze
            max_depth: Maximum call chain depth

        Returns:
            List of transitively called functions
        """
        if max_depth == 0:
            return []
        if function.function_id not in self.function_caller_callee_map:
            return []

        target_callee_ids = []
        for _, callee_ids in self.function_caller_callee_map[
            function.function_id
        ].items():
            for callee_id in callee_ids:
                target_callee_ids.append(callee_id)
        callee_functions = [
            self.function_env[callee_id] for callee_id in target_callee_ids
        ]

        for callee_function in callee_functions:
            callee_functions.extend(
                self.get_all_transitive_callee_functions(callee_function, max_depth - 1)
            )
        callee_functions = list(
            {function.function_id: function for function in callee_functions}.values()
        )
        return callee_functions

    # Helper functions retrieving call sites by callee name
    def get_callsites_by_callee_name(
        self, current_function: Function, callee_name: str
    ) -> List[Node]:
        """
        Find call sites that call a function/API by name.

        Args:
            current_function: Function to search in
            callee_name: Name of called function/API

        Returns:
            List of call site nodes
        """
        results = []
        for _, (
            single_call_site_node,
            single_callee_name,
            _,
            _,
        ) in current_function.function_call_site_nodes.items():
            if single_callee_name == callee_name:
                results.append(single_call_site_node)

        for _, (
            single_call_site_node,
            single_callee_name,
            _,
            _,
        ) in current_function.api_call_site_nodes.items():
            if single_callee_name == callee_name:
                results.append(single_call_site_node)
        return results

    ##############################################
    # Helper functions for control flow analysis #
    ##############################################

    def check_control_order(
        self, function: Function, src_line_number: int, sink_line_number: int
    ) -> bool:
        """
        Check if source line can execute before sink line.

        Args:
            function: Function containing lines
            src_line_number: Source line number
            sink_line_number: Sink line number

        Returns:
            True if source can execute before sink
        """
        src_line_number_in_function = src_line_number
        sink_line_number_in_function = sink_line_number

        if src_line_number_in_function == sink_line_number_in_function:
            return True

        for if_statement_start_line, if_statement_end_line in function.if_statements:
            (
                _,
                _,
                _,
                (true_branch_start_line, true_branch_end_line),
                (else_branch_start_line, else_branch_end_line),
            ) = function.if_statements[(if_statement_start_line, if_statement_end_line)]
            if (
                true_branch_start_line
                <= src_line_number_in_function
                <= true_branch_end_line
                and else_branch_start_line
                <= sink_line_number_in_function
                <= else_branch_end_line
                and else_branch_start_line != 0
                and else_branch_end_line != 0
            ):
                return False

        if src_line_number_in_function > sink_line_number_in_function:
            for loop_start_line, loop_end_line in function.loop_statements:
                (
                    _,
                    _,
                    _,
                    loop_body_start_line,
                    loop_body_end_line,
                ) = function.loop_statements[(loop_start_line, loop_end_line)]
                if (
                    loop_body_start_line
                    <= src_line_number_in_function
                    <= loop_body_end_line
                    and loop_body_start_line
                    <= sink_line_number_in_function
                    <= loop_body_end_line
                ):
                    return True
            return False
        return True

    def check_control_reachability(
        self, function: Function, src_line_number: int, sink_line_number: int
    ) -> bool:
        """
        Check if control can reach from source to sink line.

        Args:
            function: Function containing lines
            src_line_number: Source line number
            sink_line_number: Sink line number

        Returns:
            True if sink is reachable from source
        """
        return self.check_control_order(function, src_line_number, sink_line_number)

    # ====================================================================
    # UTILITY FUNCTIONS
    # Utility functions for AST node type maching
    # ====================================================================
    def find_all_nodes(self, root_node: Node) -> List[Node]:
        """
        Find all sub-nodes in AST recursively.

        Args:
            root_node: Root node to start from

        Returns:
            List of all nodes in tree
        """
        if root_node is None:
            return []
        nodes = [root_node]
        for child_node in root_node.children:
            nodes.extend(self.find_all_nodes(child_node))
        return nodes

    # XXX(ZZ): node_type(s) could be designed as a list of types, which will make
    # the function more flexible.
    def find_nodes_by_type(self, root_node: Node, node_type: str, k=0) -> List[Node]:
        """
        Recursively find all nodes of a given type.
        """
        nodes = []
        if k > 100:
            return []
        if root_node.type == node_type:
            nodes.append(root_node)
        for child_node in root_node.children:
            nodes.extend(self.find_nodes_by_type(child_node, node_type, k + 1))
        return nodes
