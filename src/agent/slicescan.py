import json
import os
from typing import List, Set, Tuple

from agent.agent import *
from llmtool.LLM_utils import *
from llmtool.slicescan.intra_slicer import *

from memory.state.slicescan_state import *
from memory.utils.value import *
from memory.IR.U6IR import *
from utility.request import *


class SliceScanAgent(Agent[SliceScanState]):
    """Agent for forward/backward program slicing.

    This agent analyzes code by computing forward/backward slices starting from seed values.
    It uses LLM-based analysis to identify data and control dependencies between program values/statements.
    """

    def __init__(
        self,
        project_path: str,
        language: Literal["Cpp", "Java", "Python", "Go"],
        u6ir: U6IR,
        audit_model_name: str,
        temperature: float,
        max_query_num: int,
        slice_request: SliceRequest,
        call_depth: int,
    ) -> None:
        """Initialize the slice scan agent.

        Args:
            project_path: Path to project to analyze
            language: Programming language of project
            u6ir: U6IR instance for the project
            audit_model_name: Name of LLM model for audit
            temperature: Temperature parameter for LLM
            max_query_num: Maximum number of queries to send to the LLM for re-tries
            slice_request: Slice request
            call_depth: Maximum call depth to analyze
        """

        # Initialize parent with state
        super().__init__(
            project_path,
            language,
            u6ir,
            audit_model_name,
            temperature,
            max_query_num,
            SliceScanState(),
        )

        assert language == "Cpp", "Only Cpp is supported for now."

        seed_values = []

        for function_id in u6ir.function_env:
            function = u6ir.function_env[function_id]
            if (
                function.file_path == slice_request.file_path
                and function.start_line_number
                <= slice_request.seed_line_number
                <= function.end_line_number
            ):
                seed_value = Value(
                    slice_request.seed_name,
                    ValueLabel.SRC,
                    function.file_path,
                    slice_request.seed_line_number,
                    function.function_id,
                    function.function_name,
                    slice_request.seed_line_number - function.start_line_number + 1,
                )
                self.seed_function = function
                seed_values.append(seed_value)
                break

        assert len(seed_values) == 1, "Only one seed value is supported for now."
        self.seed_value = seed_values[0]

        self.is_backward = slice_request.is_backward
        self.call_depth = call_depth

        self.state.initialize_slicescan_state(
            slice_request.slicing_request_id,
            self.seed_function,
            self.seed_value,
            self.call_depth,
            self.is_backward,
        )

        # Initialize LLM tool for intra-procedural slicing
        self.intra_slicer = IntraSlicer(
            self.audit_model_name,
            self.temperature,
            self.language,
            self.max_query_num,
            self.logger,
        )

    def scan(self) -> None:
        if self.seed_function is None:
            self.logger.print_console("No seed function found.")
            return

        self.logger.print_console("Start slice scanning in parallel...")

        # TODO: Add your implementation here.
        # You need to start from the initial seed and its function and then recursively process its callers or callees
        # You need to call the method process_slice_in_single_function to process the slice in a single function.
        # You can define any other helper functions as you need.
        work_list = [(self.seed_function, self.seed_value)]
        while work_list:
            function, value = work_list.pop(0)
            intra_slicer_output = self.process_slice_in_single_function(function, value)
            if intra_slicer_output is None:
                continue
            self.state.update_relevant_function_names_to_line_numbers(
                function.function_name, intra_slicer_output.line_numbers
            )

            # Currently, the following code is incomplete.
            # The worklist algorithm only support the intra-procedural slicing.
            for ext_value in intra_slicer_output.ext_values:
                if self.is_backward:
                    if ext_value["type"] == "Parameter":
                        # Example: Handle the parameter
                        # Hint: You need to find the call sites of the function in its caller functions
                        # and slice the caller functions from the arguments in a backward manner.
                        # You need to add each pair of caller function and argument to the work list.

                        index = ext_value["index"]
                        caller_functions = self.u6ir.get_all_caller_functions(function)

                        for caller_function in caller_functions:
                            call_site_nodes = self.u6ir.get_callsites_by_callee_name(
                                caller_function, function.function_name
                            )
                            for call_site_node in call_site_nodes:
                                call_site_id = caller_function.get_call_site_id(
                                    call_site_node
                                )
                                if call_site_id == -1:
                                    continue

                                args_at_index = caller_function.args(
                                    call_site_id=call_site_id, index=index
                                )

                                for arg in args_at_index:
                                    work_list.append(
                                        (
                                            caller_function,
                                            arg,
                                        )
                                    )
                    elif ext_value["type"] == "Output Value":
                        # TODO: Add your implementation here.
                        # Hint: You need to find the callee functions
                        # and slice the callee functions from its returned value in a backward manner.
                        # You need to add each pair of callee function and returned value to the work list.
                        pass
                else:
                    if ext_value["type"] == "Argument":
                        # TODO: Add your implementation here.
                        # Hint: You need to find the callee functions
                        # and slice the callee functions from its parameters in a forward manner.
                        # You need to add each pair of callee function and parameter to the work list.
                        pass
                    elif ext_value["type"] == "Return Value":
                        # TODO: Add your implementation here.
                        # Hint: You need to find the call sites of the function in its caller functions
                        # and slice the caller functions from the output value (i.e., call expression) in a forward manner.
                        # You need to add each pair of caller function and output value to the work list.
                        pass

        state_dict = self.state.to_dict()
        request_id = self.state._slicing_request_id
        slice_info_fn = f"slice_info_{request_id}.json"
        with open(self.res_dir_path + "/" + slice_info_fn, "w") as slice_info_file:
            json.dump(self.state.to_dict(), slice_info_file, indent=4)
        self.logger.print_console(
            "The slicing result is saved in " + self.res_dir_path + "/" + slice_info_fn
        )

    def process_slice_in_single_function(
        self, function: Function, value: Value
    ) -> Optional[IntraSlicerOutput]:
        """Process the slice in a single function.

        Args:
            function: The function to process
            value: The value as the seed value for slicing in the function
        """
        intra_slicer_input = IntraSlicerInput(function, [value], self.is_backward)
        intra_slicer_output = self.intra_slicer.invoke(intra_slicer_input)
        return intra_slicer_output

    def finalize(self) -> U6IR:
        """Finalize the bug scanning process for persistence."""
        # Currently, we do not update the U6IR
        return self.u6ir
