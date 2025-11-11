"""
Tree-sitter based code analyzer module.
Provides functionality for parsing and analyzing source code using tree-sitter.
"""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
import concurrent.futures
import sys
import threading
from typing import Dict, List, Optional, Set, Tuple

from tree_sitter import Language, Node, Parser, Tree
from tqdm import tqdm

from memory.utils.function import *
from memory.utils.api import *
from memory.utils.value import *
from memory.IR.U6IR import *


class TSAnalyzer(ABC):
    """
    Abstract base class for tree-sitter based code analysis.
    Provides functionality for parsing and analyzing source code.
    """

    def __init__(
        self,
        code_in_files: Dict[str, str],
        language_name: str,
        max_symbolic_workers_num=10,
    ) -> None:
        """
        Initialize the analyzer with source code and configuration.

        Args:
            code_in_files: Dict mapping file paths to source contents
            language_name: Programming language name
            max_symbolic_workers_num: Max parallel workers for analysis
        """
        self.code_in_files = code_in_files
        cwd = Path(__file__).resolve().parent.absolute()
        TSPATH = cwd / "../../../lib/build/"
        language_path = TSPATH / "my-languages.so"
        self.max_symbolic_workers_num = max_symbolic_workers_num
        self.u6ir = U6IR(code_in_files)

        # Initialize tree-sitter parser
        self.parser = Parser()
        self.language_name = language_name
        if language_name == "C":
            self.language = Language(str(language_path), "c")
        elif language_name == "Cpp":
            self.language = Language(str(language_path), "cpp")
        elif language_name == "Java":
            self.language = Language(str(language_path), "java")
        elif language_name == "Python":
            self.language = Language(str(language_path), "python")
        elif language_name == "Go":
            self.language = Language(str(language_path), "go")
        else:
            raise RAValueError("Invalid language setting")
        self.parser.set_language(self.language)

    def run(self) -> U6IR:
        """
        Run the analyzer.

        Returns:
            U6IR: The U6IR object containing the analysis results
        """
        self._parse_project()
        self._analyze_call_graph()
        return self.u6ir

    ##################################################
    #   Wrapper functions for project AST parsing    #
    # (Only used by the TSAnalyzer class/subclasses) #
    ##################################################

    def _parse_single_file(self, file_path: str, source_code: str) -> Tuple[str, str]:
        """
        Parse a single source file and extract function/global info.

        Args:
            file_path: Path to source file
            source_code: File contents

        Returns:
            Tuple of file path and source code
        """
        try:
            tree = self.parser.parse(bytes(source_code, "utf8"))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            raise e
        # Call user-defined processing.
        self._extract_function_raw_info(file_path, source_code, tree)
        self._extract_global_info(file_path, source_code, tree)
        return file_path, source_code

    def _analyze_single_function(
        self, function_id: int, raw_data: Tuple[Node, str, int, int]
    ) -> Tuple[int, Function]:
        """
        Analyze a single function and extract metadata.

        Args:
            function_id: ID of function to analyze
            raw_data: Tuple of function node, name, start/end lines

        Returns:
            Tuple of function ID and analyzed Function object
        """
        (function_node, name, start_line_number, end_line_number) = raw_data
        file_name = self.u6ir.functionToFile[function_id]
        file_content = self.u6ir.fileContentDic[file_name]
        function_code = file_content[function_node.start_byte : function_node.end_byte]
        current_function = Function(
            function_id,
            name,
            function_code,
            start_line_number,
            end_line_number,
            function_node,
            file_name,
        )
        current_function = self._extract_meta_data_in_single_function(current_function)
        return function_id, current_function

    def _parse_project(self) -> None:
        """
        Wrapper function to parse all project files using tree-sitter.
        """

        # XXX (ZZ): There is likely a mypy error here. We seperate the parsing of files and functions
        # into two functions to avoid the mypy error.
        def parse_files():
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_symbolic_workers_num
            ) as executor:
                futures = {}
                pbar = tqdm(total=len(self.u6ir.code_in_files), desc="Parsing files")
                for file_path, source_code in self.u6ir.code_in_files.items():
                    # Submit a task for each file.
                    future = executor.submit(
                        self._parse_single_file, file_path, source_code
                    )
                    futures[future] = file_path
                # Collect results.
                for future in concurrent.futures.as_completed(futures):
                    file_path, source = future.result()
                    self.u6ir.fileContentDic[file_path] = source
                    pbar.update(1)
                pbar.close()

        def parse_functions():
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_symbolic_workers_num
            ) as executor:
                futures = {}
                pbar = tqdm(
                    total=len(self.u6ir.functionRawDataDic), desc="Analyzing functions"
                )
                for function_id, raw_data in self.u6ir.functionRawDataDic.items():
                    future = executor.submit(
                        self._analyze_single_function, function_id, raw_data
                    )
                    futures[future] = function_id

                for future in concurrent.futures.as_completed(futures):
                    func_id, current_function = future.result()
                    self.u6ir.function_env[func_id] = current_function
                    pbar.update(1)
                pbar.close()

        parse_files()
        parse_functions()
        return

    def _analyze_call_graph(self) -> None:
        """
        Analyze the call graph of the project in a parallel manner.
        """
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_symbolic_workers_num
        ) as executor:
            futures = {}
            pbar = tqdm(total=len(self.u6ir.function_env), desc="Analyzing call graphs")
            for function_id, current_function in self.u6ir.function_env.items():
                future = executor.submit(
                    self._extract_call_graph_edges, current_function
                )
                futures[future] = function_id
            for future in concurrent.futures.as_completed(futures):
                # Optionally, process or log each completed task here.
                pbar.update(1)
            pbar.close()
        return

    ######################################################
    #        Extractors for function raw/meta data       #
    #   (Only used by the TSAnalyzer class/subclasses)   #
    ######################################################
    @abstractmethod
    def _extract_function_raw_info(
        self, file_path: str, source_code: str, tree: Tree
    ) -> None:
        """
        Extract function raw information from a source file.
        :param file_path: Path of the source file.
        :param source_code: Content of the source file.
        :param tree: Parsed syntax tree.
        """
        pass

    def _extract_meta_data_in_single_function(
        self, current_function: Function
    ) -> Function:
        """
        Extract meta data for a single function, including
        1. Parameters and return values
        2. If-statements and loop statements
        Attention: Call sites, arguments, and output values are not extracted

        :param current_function: The function to be analyzed.
        """
        file_name = self.u6ir.functionToFile[current_function.function_id]
        file_content = self.u6ir.fileContentDic[file_name]

        self._extract_parameters_in_single_function(current_function)
        self._extract_return_values_in_single_function(current_function)
        self._extract_if_statements(current_function, file_content)
        self._extract_loop_statements(current_function, file_content)
        return current_function

    @abstractmethod
    def _extract_global_info(
        self, file_path: str, source_code: str, tree: Tree
    ) -> None:
        """
        Extract macro or global variable information from a source file.
        :param file_path: Path of the source file.
        :param source_code: Content of the source file.
        :param tree: Parsed syntax tree.
        """
        pass

    #########################################################
    #         Helper function for call graph analysis       #
    #     (Only used by the TSAnalyzer class/subclasses)    #
    #########################################################

    def _extract_call_graph_edges(self, current_function: Function) -> None:
        """
        Extract call graph edges for a function.

        Args:
            current_function: Function to analyze
        """
        file_name = self.u6ir.functionToFile[current_function.function_id]
        file_content = self.u6ir.fileContentDic[file_name]

        call_node_type = None
        if self.language_name == "C" or self.language_name == "Cpp":
            call_node_type = "call_expression"
        elif self.language_name == "Java":
            call_node_type = "method_invocation"
        elif self.language_name == "Python":
            call_node_type = "call"
        elif self.language_name == "Go":
            call_node_type = "call_expression"

        assert call_node_type != None

        all_call_sites = self.u6ir.find_nodes_by_type(
            current_function.parse_tree_root_node, call_node_type
        )

        # Collect all call sites
        for call_site_node in all_call_sites:
            call_site_id = len(current_function.all_call_site_nodes)
            start_line_number = (
                file_content[: call_site_node.start_byte].count("\n")
                + 1
                - current_function.start_line_number
                + 1
            )
            end_line_number = (
                file_content[: call_site_node.end_byte].count("\n")
                + 1
                - current_function.start_line_number
                + 1
            )
            callee_name = (
                file_content[call_site_node.start_byte : call_site_node.end_byte]
                .split("(")[0]
                .strip()
            )
            current_function.all_call_site_nodes[call_site_id] = (
                call_site_node,
                callee_name,
                start_line_number,
                end_line_number,
            )

        # Collect call sites of user-defined functions and library APIs and build caller-callee relationships
        for call_site_id, (
            call_site_node,
            callee_name,
            start_line_number,
            end_line_number,
        ) in current_function.all_call_site_nodes.items():
            self._extract_arguments_in_single_function_at_callsite(
                current_function, call_site_id, call_site_node
            )
            self._extract_receiver_arguments_in_single_function_at_callsite(
                current_function, call_site_id, call_site_node
            )
            self._extract_output_values_in_single_function_at_callsite(
                current_function, call_site_id, call_site_node
            )

            callee_ids = self._extract_callee_function_ids_at_callsite(
                current_function, call_site_id, call_site_node
            )

            if len(callee_ids) > 0:
                current_function.function_call_site_nodes[call_site_id] = (
                    call_site_node,
                    callee_name,
                    start_line_number,
                    end_line_number,
                )

                # Update the caller-callee relationship between user-defined functions
                for callee_id in callee_ids:
                    caller_id = current_function.function_id
                    with self.u6ir.function_caller_callee_map_lock:
                        if caller_id not in self.u6ir.function_caller_callee_map:
                            self.u6ir.function_caller_callee_map[caller_id] = {}
                        if (
                            call_site_id
                            not in self.u6ir.function_caller_callee_map[caller_id]
                        ):
                            self.u6ir.function_caller_callee_map[caller_id][
                                call_site_id
                            ] = set()
                        self.u6ir.function_caller_callee_map[caller_id][
                            call_site_id
                        ].add(callee_id)
                    with self.u6ir.function_callee_caller_map_lock:
                        if callee_id not in self.u6ir.function_callee_caller_map:
                            self.u6ir.function_callee_caller_map[callee_id] = set()
                        self.u6ir.function_callee_caller_map[callee_id].add(
                            (call_site_id, caller_id)
                        )
            else:
                current_function.api_call_site_nodes[call_site_id] = (
                    call_site_node,
                    callee_name,
                    start_line_number,
                    end_line_number,
                )

                api_id: Optional[int] = None
                arguments = current_function.args(call_site_id=call_site_id)
                api_template = API(-1, callee_name, len(arguments))

                # Insert the API into the API environment if it does not exist previously
                with self.u6ir.api_env_lock:
                    # First check if the API already exists
                    api_id = None
                    for single_api_id, single_api in self.u6ir.api_env.items():
                        if single_api == api_template:
                            api_id = single_api_id
                            break

                    # If not found, create a new API
                    if api_id is None:
                        next_id = len(self.u6ir.api_env)
                        self.u6ir.api_env[next_id] = API(
                            next_id, callee_name, len(arguments)
                        )
                        api_id = next_id

                caller_id = current_function.function_id
                # Update the caller-callee relationship between user-defined functions and library APIs
                with self.u6ir.function_caller_api_callee_map_lock:
                    if caller_id not in self.u6ir.function_caller_api_callee_map:
                        self.u6ir.function_caller_api_callee_map[caller_id] = {}
                    if (
                        call_site_id
                        not in self.u6ir.function_caller_api_callee_map[caller_id]
                    ):
                        self.u6ir.function_caller_api_callee_map[caller_id][
                            call_site_id
                        ] = set()
                    self.u6ir.function_caller_api_callee_map[caller_id][
                        call_site_id
                    ].add(api_id)
                with self.u6ir.api_callee_function_caller_map_lock:
                    if api_id not in self.u6ir.api_callee_function_caller_map:
                        self.u6ir.api_callee_function_caller_map[api_id] = set()
                    self.u6ir.api_callee_function_caller_map[api_id].add(
                        (call_site_id, caller_id)
                    )
        return

    @abstractmethod
    def _extract_callee_name_at_call_site(self, node: Node, source_code: str) -> str:
        """
        Get callee name at call site.

        Args:
            node: Call site node
            source_code: Source code content

        Returns:
            Name of called function/API
        """
        pass

    def _extract_callee_function_ids_at_callsite(
        self, current_function: Function, call_site_id: int, call_site_node: Node
    ) -> List[int]:
        """
        Get IDs of functions called at a call site.

        Args:
            current_function: Function containing call
            call_site_id: ID of call site
            call_site_node: Call site AST node

        Returns:
            List of callee function IDs
        """
        file_name = current_function.file_path
        source_code = self.u6ir.code_in_files[file_name]
        callee_name = self._extract_callee_name_at_call_site(
            call_site_node, source_code
        )
        arguments = current_function.args(call_site_id=call_site_id)

        temp_callee_ids = []
        # while callee_name in self.u6ir.glb_var_map:
        #     callee_name = self.u6ir.glb_var_map[callee_name]
        if callee_name in self.u6ir.functionNameToId:
            temp_callee_ids.extend(list(self.u6ir.functionNameToId[callee_name]))

        # Check parameter count matches the arguments count.
        callee_ids = []
        for callee_id in temp_callee_ids:
            callee = self.u6ir.function_env[callee_id]

            # Check receiver arguments/parameters
            callee_receiver_para = callee.paras(ValueLabel.OBJ_PARA)
            receiver_args = current_function.args(
                call_site_id=call_site_id, arg_label=ValueLabel.OBJ_ARG
            )
            if (len(receiver_args) == 0 and len(callee_receiver_para) > 0) or (
                len(receiver_args) > 0 and len(callee_receiver_para) == 0
            ):
                # If the callee has no receiver parameter but the callsite has one, or vice versa, skip this callee
                continue

            # Check parameter count
            callee_paras = callee.paras(ValueLabel.PARA)
            # The code `callee_variadic_para` is not valid Python syntax. It seems like a placeholder
            # or a comment. It does not perform any specific action or functionality in Python.
            callee_variadic_para = callee.paras(ValueLabel.VARI_PARA)
            if len(callee_variadic_para) == 0:
                if len(callee_paras) == len(arguments):
                    callee_ids.append(callee_id)
            else:
                if len(callee_paras) <= len(arguments):
                    callee_ids.append(callee_id)
        return callee_ids

    ############################################################
    #   Helper functions for para/arg/out/ret value extraction #
    #      (Only used by the TSAnalyzer class/subclasses)      #
    ############################################################

    # Helper functions for parameters
    @abstractmethod
    def _extract_parameters_in_single_function(
        self, current_function: Function
    ) -> None:
        """
        Extract function parameters.

        Args:
            current_function: Function to analyze
        """
        pass

    # Helper functions for return values
    @abstractmethod
    def _extract_return_values_in_single_function(
        self, current_function: Function
    ) -> None:
        """
        Extract function return values.

        Args:
            current_function: Function to analyze
        """
        pass

    # Helper functions for arguments
    @abstractmethod
    def _extract_arguments_in_single_function_at_callsite(
        self, current_function: Function, call_site_id: int, call_site_node: Node
    ) -> None:
        """
        Extract arguments at a call site.

        Args:
            current_function: Function containing call
            call_site_id: ID of call site
            call_site_node: Call site AST node
        """
        pass

    # Helper functions for receiver arguments
    @abstractmethod
    def _extract_receiver_arguments_in_single_function_at_callsite(
        self, current_function: Function, call_site_id: int, call_site_node: Node
    ) -> None:
        """
        Extract receiver arguments at a call site.

        Args:
            current_function: Function containing call
            call_site_id: ID of call site
            call_site_node: Call site AST node
        """
        pass

    # Helper functions for output values
    def _extract_output_values_in_single_function_at_callsite(
        self, current_function: Function, call_site_id: int, call_site_node: Node
    ) -> None:
        """
        Extract output values at a call site.

        Args:
            current_function: Function containing call
            call_site_id: ID of call site
            call_site_node: Call site AST node
        """
        file_code = self.u6ir.code_in_files[current_function.file_path]
        name = file_code[call_site_node.start_byte : call_site_node.end_byte]
        line_number = file_code[: call_site_node.start_byte].count("\n") + 1
        output_value = Value(
            name,
            ValueLabel.OUT,
            current_function.file_path,
            line_number,
            current_function.function_id,
            current_function.function_name,
            line_number - current_function.start_line_number + 1,
            -1,
        )
        current_function.add_outval(call_site_id, output_value)
        return

    #####################################################
    #        Extractors of branches and loops           #
    # (Only used by the TSAnalyzer class/subclasses)    #
    #####################################################
    @abstractmethod
    def _extract_if_statements(self, function: Function, source_code: str) -> None:
        """
        Extract if statements from function.

        Args:
            function: Function to analyze
            source_code: Source code content
        """
        pass

    @abstractmethod
    def _extract_loop_statements(self, function: Function, source_code: str) -> None:
        """
        Extract loop statements from function.

        Args:
            function: Function to analyze
            source_code: Source code content
        """
        pass
