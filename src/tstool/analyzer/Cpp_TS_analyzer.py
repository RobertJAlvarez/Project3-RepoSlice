from os import path
import sys
from typing import Dict, List, Optional, Set, Tuple
import tree_sitter

from .TS_analyzer import *
from memory.utils.function import *
from memory.utils.value import *


class Cpp_TSAnalyzer(TSAnalyzer):
    """TSAnalyzer for C/C++ source files using tree-sitter.

    Implements language-specific parsing and analysis functionality for C/C++ code.
    Handles function definitions, macros, parameters, return values, control flow etc.
    """

    def __init__(
        self,
        code_in_files: Dict[str, str],
        language_name: str,
        max_symbolic_workers_num=10,
    ) -> None:
        super().__init__(code_in_files, language_name, max_symbolic_workers_num)

    def _extract_function_raw_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """Extract raw function information from C/C++ source file.

        Parses function definitions and stores basic metadata like name, location etc.

        Args:
            file_path: Path to the source file
            source_code: Content of the source file
            tree: Parsed syntax tree
        """
        for func_def_node in self.u6ir.find_nodes_by_type(
            tree.root_node, "function_definition"
        ):
            for func_decl_node in self.u6ir.find_nodes_by_type(
                func_def_node, "function_declarator"
            ):
                decl_start_line = func_decl_node.start_point[0] + 1
                def_start_line = func_def_node.start_point[0] + 1
                # Only keep the declarator that is on the same line as the definition
                # or the next line
                if (
                    decl_start_line != def_start_line
                    and decl_start_line != def_start_line + 1
                ):
                    continue
                function_name = ""
                for node in func_decl_node.children:
                    if node.type in {"identifier", "field_identifier"}:
                        function_name = node.text.decode("utf-8")
                        break
                    elif node.type == "qualified_identifier":
                        qualified_name = node.text.decode("utf-8")
                        function_name = qualified_name.split("::")[-1]
                        break
                if not function_name:
                    continue

                start_line = source_code[: func_def_node.start_byte].count("\n") + 1
                end_line = source_code[: func_def_node.end_byte].count("\n") + 1
                function_id = len(self.u6ir.functionRawDataDic) + 1

                self.u6ir.functionRawDataDic[function_id] = (
                    func_def_node,
                    function_name,
                    start_line,
                    end_line,
                )
                self.u6ir.functionToFile[function_id] = file_path

                if function_name not in self.u6ir.functionNameToId:
                    self.u6ir.functionNameToId[function_name] = set()
                self.u6ir.functionNameToId[function_name].add(function_id)

    def _extract_global_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """Extract macro and global variable information from C/C++ source file.

        Parses macro definitions and function-like macros.

        Args:
            file_path: Path to the source file
            source_code: Content of the source file
            tree: Parsed syntax tree
        """
        # Extract regular macro definitions
        for macro_node in self.u6ir.find_nodes_by_type(tree.root_node, "preproc_def"):
            macro_name = ""
            macro_def = ""
            for child in macro_node.children:
                if child.type == "identifier":
                    macro_name = child.text.decode("utf-8")
                if child.type == "preproc_arg":
                    macro_def = child.text.decode("utf-8")
            if macro_name and macro_def:
                self.u6ir.glb_var_map[macro_name] = macro_def

        # Extract function-like macro definitions
        for macro_func_node in self.u6ir.find_nodes_by_type(
            tree.root_node, "preproc_function_def"
        ):
            function_name = ""
            for child in macro_func_node.children:
                if child.type == "identifier":
                    function_name = child.text.decode("utf-8")
                if child.type == "preproc_params":
                    function_name += child.text.decode("utf-8")
            if not function_name:
                continue

            start_line = source_code[: macro_func_node.start_byte].count("\n") + 1
            end_line = source_code[: macro_func_node.end_byte].count("\n") + 1
            function_id = len(self.u6ir.functionRawDataDic) + 1

            self.u6ir.functionRawDataDic[function_id] = (
                macro_func_node,
                function_name,
                start_line,
                end_line,
            )
            self.u6ir.functionToFile[function_id] = file_path

            if function_name not in self.u6ir.functionNameToId:
                self.u6ir.functionNameToId[function_name] = set()
            self.u6ir.functionNameToId[function_name].add(function_id)

    def _extract_callee_name_at_call_site(
        self, node: tree_sitter.Node, source_code: str
    ) -> str:
        """Extract callee function name from a call site.

        Handles member function calls with dot/arrow operators.

        Args:
            node: Call site AST node
            source_code: Source file content

        Returns:
            Name of the called function
        """
        sub_nodes = []
        for child in node.children:
            if child.type == "identifier":
                sub_nodes.append(child)
            else:
                sub_nodes.extend(child.children)
            break

        node_texts = [node.text.decode("utf-8") for node in sub_nodes]
        if not node_texts:
            return ""

        dot_idx = (
            len(node_texts) - 1 - node_texts[::-1].index(".")
            if "." in node_texts
            else -1
        )
        arrow_idx = (
            len(node_texts) - 1 - node_texts[::-1].index("->")
            if "->" in node_texts
            else -1
        )
        return node_texts[max(dot_idx, arrow_idx) + 1]

    def _extract_parameters_in_single_function(
        self, current_function: Function
    ) -> None:
        """Extract function parameters and update Function object.

        Args:
            current_function: Function to analyze
        """
        file_content = self.u6ir.code_in_files[current_function.file_path]
        param_nodes = self.u6ir.find_nodes_by_type(
            current_function.parse_tree_root_node, "parameter_declaration"
        )

        for idx, param_node in enumerate(param_nodes):
            for id_node in self.u6ir.find_nodes_by_type(param_node, "identifier"):
                param_name = id_node.text.decode("utf-8")
                line_num = file_content[: id_node.start_byte].count("\n") + 1
                current_function.add_para(
                    Value(
                        param_name,
                        ValueLabel.PARA,
                        current_function.file_path,
                        line_num,
                        current_function.function_id,
                        current_function.function_name,
                        line_num - current_function.start_line_number + 1,
                        idx,
                    )
                )
                break

    def _extract_return_values_in_single_function(
        self, current_function: Function
    ) -> None:
        """Extract return values from function and update Function object.

        Args:
            current_function: Function to analyze
        """
        file_content = self.u6ir.code_in_files[current_function.file_path]
        for ret_node in self.u6ir.find_nodes_by_type(
            current_function.parse_tree_root_node, "return_statement"
        ):
            line_num = file_content[: ret_node.start_byte].count("\n") + 1
            ret_stmt = ret_node.text.decode("utf-8")
            ret_val = ret_stmt.replace("return", "").strip()
            current_function.add_retval(
                Value(
                    ret_val,
                    ValueLabel.RET,
                    current_function.file_path,
                    line_num,
                    current_function.function_id,
                    current_function.function_name,
                    line_num - current_function.start_line_number + 1,
                    0,
                )
            )

    def _extract_arguments_in_single_function_at_callsite(
        self,
        current_function: Function,
        call_site_id: int,
        call_site_node: tree_sitter.Node,
    ) -> None:
        """Extract function call arguments and update Function object.

        Args:
            current_function: Function containing the call
            call_site_id: ID of the call site
            call_site_node: Call site AST node
        """
        source_code = self.u6ir.code_in_files[current_function.file_path]
        arg_idx = 0

        for node in call_site_node.children:
            if node.type == "argument_list":
                for arg_node in node.children[1:-1]:
                    if arg_node.type != ",":
                        line_num = source_code[: arg_node.start_byte].count("\n") + 1
                        current_function.add_arg(
                            call_site_id,
                            Value(
                                arg_node.text.decode("utf-8"),
                                ValueLabel.ARG,
                                current_function.file_path,
                                line_num,
                                current_function.function_id,
                                current_function.function_name,
                                line_num - current_function.start_line_number + 1,
                                arg_idx,
                            ),
                        )
                        arg_idx += 1

    def _extract_receiver_arguments_in_single_function_at_callsite(
        self, current_function: Function, call_site_id: int, call_site_node: Node
    ) -> None:
        """Extract receiver arguments from method calls.

        Currently a no-op for C++.

        Args:
            current_function: Function containing the call
            call_site_id: ID of the call site
            call_site_node: Call site AST node
        """
        return

    def _extract_if_statements(self, function: Function, source_code: str) -> None:
        """Extract if statements and update Function object.

        Args:
            function: Function to analyze
            source_code: Source file content
        """
        for if_node in self.u6ir.find_nodes_by_type(
            function.parse_tree_root_node, "if_statement"
        ):
            cond_str = ""
            cond_start = cond_end = 0
            true_start = true_end = 0
            else_start = else_end = 0

            for child in if_node.children:
                if child.type in ["parenthesized_expression", "condition_clause"]:
                    cond_start = source_code[: child.start_byte].count("\n") + 1
                    cond_end = source_code[: child.end_byte].count("\n") + 1
                    cond_str = child.text.decode("utf-8")
                elif "statement" in child.type:
                    true_start = source_code[: child.start_byte].count("\n") + 1
                    true_end = source_code[: child.end_byte].count("\n") + 1
                elif child.type == "else_clause":
                    else_start = source_code[: child.start_byte].count("\n") + 1
                    else_end = source_code[: child.end_byte].count("\n") + 1

            if_start = source_code[: if_node.start_byte].count("\n") + 1
            if_end = source_code[: if_node.end_byte].count("\n") + 1
            function.if_statements[(if_start, if_end)] = (
                cond_start,
                cond_end,
                cond_str,
                (true_start, true_end),
                (else_start, else_end),
            )

    def _extract_loop_statements(self, function: Function, source_code: str) -> None:
        """Extract loop statements and update Function object.

        Handles both for and while loops.

        Args:
            function: Function to analyze
            source_code: Source file content
        """
        # Extract for loops
        for loop_node in self.u6ir.find_nodes_by_type(
            function.parse_tree_root_node, "for_statement"
        ):
            loop_start = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end = source_code[: loop_node.end_byte].count("\n") + 1

            header_start = header_end = 0
            header_str = ""
            body_start = body_end = 0
            header_start_byte = header_end_byte = 0

            for child in loop_node.children:
                if child.type == "(":
                    header_start = source_code[: child.start_byte].count("\n") + 1
                    header_start_byte = child.end_byte
                elif child.type == ")":
                    header_end = source_code[: child.end_byte].count("\n") + 1
                    header_end_byte = child.start_byte
                    header_str = source_code[header_start_byte:header_end_byte]
                elif child.type == "block":
                    body_lines = []
                    for stmt in child.children:
                        if stmt.type not in {"{", "}"}:
                            body_lines.extend(
                                [
                                    source_code[: stmt.start_byte].count("\n") + 1,
                                    source_code[: stmt.end_byte].count("\n") + 1,
                                ]
                            )
                    if body_lines:
                        body_start = min(body_lines)
                        body_end = max(body_lines)
                    else:
                        body_start = body_end = header_end
                elif "statement" in child.type:
                    body_start = source_code[: child.start_byte].count("\n") + 1
                    body_end = source_code[: child.end_byte].count("\n") + 1

            function.loop_statements[(loop_start, loop_end)] = (
                header_start,
                header_end,
                header_str,
                body_start,
                body_end,
            )

        # Extract while loops
        for loop_node in self.u6ir.find_nodes_by_type(
            function.parse_tree_root_node, "while_statement"
        ):
            loop_start = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end = source_code[: loop_node.end_byte].count("\n") + 1

            header_start = header_end = 0
            header_str = ""
            body_start = body_end = 0

            for child in loop_node.children:
                if child.type == "parenthesized_expression":
                    header_start = source_code[: child.start_byte].count("\n") + 1
                    header_end = source_code[: child.end_byte].count("\n") + 1
                    header_str = child.text.decode("utf-8")
                elif "statement" in child.type:
                    body_lines = []
                    for stmt in child.children:
                        if stmt.type not in {"{", "}"}:
                            body_lines.extend(
                                [
                                    source_code[: stmt.start_byte].count("\n") + 1,
                                    source_code[: stmt.end_byte].count("\n") + 1,
                                ]
                            )
                    if body_lines:
                        body_start = min(body_lines)
                        body_end = max(body_lines)
                    else:
                        body_start = body_end = header_end

            function.loop_statements[(loop_start, loop_end)] = (
                header_start,
                header_end,
                header_str,
                body_start,
                body_end,
            )
