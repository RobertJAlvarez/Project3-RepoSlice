import argparse
from ast import Continue
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple

from agent.slicescan import SliceScanAgent
from memory.IR.U6IR import U6IR

from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from utility.errors import *
from utility.request import *


BASE_PATH = Path(__file__).resolve().parents[1]


class RepoSlice:
    def __init__(
        self,
        args: argparse.Namespace,
    ):
        """
        Initialize BatchScan object with project details.
        """
        # argument format check
        self.args = args

        self.slice_request_path = args.slice_request_path
        self.language = args.language
        self.max_symbolic_workers = args.max_symbolic_workers
        self.max_query_num = args.max_query_num
        self.audit_model_name = args.audit_model_name
        self.temperature = args.temperature
        self.call_depth = args.call_depth
        self.is_backward = args.is_backward

        with open(self.slice_request_path, "r") as f:
            self.slice_request = SliceRequest.from_dict(json.load(f))

        print(self.slice_request.description())

        # Extract project path and name from slice request
        self.project_path = str(Path(self.slice_request.project_path))
        self.project_name = Path(self.project_path).name

        # Initialize code storage
        self.code_in_files: Dict[str, str] = {}

        assert self.language == "Cpp", "Only Cpp is supported for now."
        suffixs = ["cpp", "cc", "hpp", "c", "h"]
        self.traverse_files(self.project_path, suffixs)

        # Build the U6IR of the project
        self.ts_analyzer = Cpp_TSAnalyzer(
            self.code_in_files,
            self.language,
            self.max_symbolic_workers,
        )

    def traverse_files(self, project_path: str, suffixes: List[str]) -> None:
        """Traverse the project directory and collect source code files.

        Args:
            project_path: Root path of the project to analyze
            suffixes: List of file extensions to include (without dots)
        """
        project_root = Path(project_path)

        if not project_root.exists():
            raise RAValueError(f"Project path does not exist: {project_path}")

        if not project_root.is_dir():
            raise RAValueError(f"Project path is not a directory: {project_path}")

        # Clear existing files
        self.code_in_files.clear()

        # Traverse all files recursively
        for file_path in project_root.rglob("*"):
            if file_path.is_file():
                # Check if file has a matching suffix
                if any(file_path.name.endswith(f".{suffix}") for suffix in suffixes):
                    try:
                        # Read file content
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()

                        # Store with absolute path as key
                        self.code_in_files[str(file_path.absolute())] = content

                    except (OSError, IOError) as e:
                        print(f"Warning: Could not read file {file_path}: {e}")
                        continue

        if not self.code_in_files:
            print(
                f"Warning: No source files found with extensions {suffixes} in {project_path}"
            )

    def run(self):
        self.ts_analyzer.run()

        self.slice_scan_agent = SliceScanAgent(
            self.project_path,
            self.language,
            self.ts_analyzer.u6ir,
            self.audit_model_name,
            self.temperature,
            self.max_query_num,
            self.slice_request,
            self.call_depth,
        )
        self.slice_scan_agent.run()


def configure_args():
    parser = argparse.ArgumentParser(
        description="RepoSlice: Run inter-procedural program slicer"
    )

    parser.add_argument(
        "--slice-request-path",
        required=True,
        help="A json file containing the slice request",
    )
    parser.add_argument("--language", required=True, help="Programming language")

    parser.add_argument(
        "--max-symbolic-workers",
        type=int,
        default=30,
        help="Max symbolic workers for parsing-based analysis",
    )

    parser.add_argument(
        "--max-query-num",
        type=int,
        default=30,
        help="Maximum number of queries to send to the LLM",
    )

    parser.add_argument(
        "--audit-model-name", default="gpt-5-mini", help="The name of LLMs"
    )

    parser.add_argument(
        "--temperature", type=float, default=0.5, help="Temperature for inference"
    )
    parser.add_argument("--call-depth", type=int, default=3, help="Call depth setting")

    # Parameters for slicescan
    parser.add_argument(
        "--is-backward", action="store_true", help="Flag for backward slicing"
    )

    args = parser.parse_args()
    return args


def main() -> None:
    args = configure_args()
    reposlice = RepoSlice(args)
    reposlice.run()
    return


if __name__ == "__main__":
    main()
