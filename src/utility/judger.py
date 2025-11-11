"""Judger module for comparing slice results with oracle data."""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple


def load_json_file(file_path: str) -> dict:
    """Load JSON file and return its contents.

    Args:
        file_path: Path to the JSON file

    Returns:
        Dictionary containing the JSON data

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_whitelist(line_numbers: List[int], whitelist: List[int]) -> List[int]:
    """Filter out whitelist line numbers from a list.

    Args:
        line_numbers: List of line numbers to filter
        whitelist: List of line numbers to exclude

    Returns:
        Filtered list of line numbers
    """
    whitelist_set = set(whitelist)
    return [ln for ln in line_numbers if ln not in whitelist_set]


def compare_function_lines(
    result_lines: List[int], oracle_lines: List[int], whitelist: List[int]
) -> Tuple[int, int, int]:
    """Compare line numbers for a single function.

    Args:
        result_lines: Line numbers from the result
        oracle_lines: Line numbers from the oracle
        whitelist: Line numbers to exclude from comparison

    Returns:
        Tuple of (true_positives, false_positives, false_negatives)
    """
    # Filter out whitelist line numbers
    result_filtered = set(filter_whitelist(result_lines, whitelist))
    oracle_filtered = set(filter_whitelist(oracle_lines, whitelist))

    # Calculate metrics
    true_positives = len(result_filtered & oracle_filtered)
    false_positives = len(result_filtered - oracle_filtered)
    false_negatives = len(oracle_filtered - result_filtered)

    return true_positives, false_positives, false_negatives


def judge_slice_result(
    slice_request_id: str, result_json_path: str, oracle_dir: str
) -> Dict:
    """Compare slice result with oracle data.

    Args:
        slice_request_id: The ID of the slice request (e.g., "slice_request_forward_01")
        result_json_path: Path to the result JSON file
        oracle_dir: Directory containing oracle files (default: "oracle" relative to project root)

    Returns:
        Dictionary containing precision, recall, f1_score, and detailed metrics

    Raises:
        FileNotFoundError: If oracle or result file doesn't exist
        KeyError: If required keys are missing from JSON files
    """
    # Determine oracle directory
    oracle_dir_path = Path(oracle_dir)

    # Load oracle file
    oracle_path = oracle_dir_path / f"{slice_request_id}.json"
    if not oracle_path.exists():
        raise FileNotFoundError(f"Oracle file not found: {oracle_path}")

    oracle_data = load_json_file(str(oracle_path))

    # Load result file
    if not os.path.exists(result_json_path):
        raise FileNotFoundError(f"Result file not found: {result_json_path}")

    result_data = load_json_file(result_json_path)

    # Extract relevant data
    oracle_relevant = oracle_data.get("relevant_function_names_to_line_numbers", {})
    oracle_whitelist = oracle_data.get("whitelist_line_numbers", {})
    result_relevant = result_data.get("relevant_function_names_to_line_numbers", {})

    # Initialize metrics
    total_tp = 0
    total_fp = 0
    total_fn = 0
    function_metrics = {}

    # Get all function names from both oracle and result
    all_functions = set(oracle_relevant.keys()) | set(result_relevant.keys())

    # Compare each function
    for function_name in all_functions:
        result_lines = result_relevant.get(function_name, [])
        oracle_lines = oracle_relevant.get(function_name, [])
        whitelist = oracle_whitelist.get(function_name, [])

        tp, fp, fn = compare_function_lines(result_lines, oracle_lines, whitelist)

        total_tp += tp
        total_fp += fp
        total_fn += fn

        # Calculate per-function metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        function_metrics[function_name] = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
        }

    # Calculate overall metrics
    overall_precision = (
        total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    )
    overall_recall = (
        total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    )
    overall_f1 = (
        2 * overall_precision * overall_recall / (overall_precision + overall_recall)
        if (overall_precision + overall_recall) > 0
        else 0.0
    )

    return {
        "slice_request_id": slice_request_id,
        "overall_metrics": {
            "true_positives": total_tp,
            "false_positives": total_fp,
            "false_negatives": total_fn,
            "precision": overall_precision,
            "recall": overall_recall,
            "f1_score": overall_f1,
        },
        "function_metrics": function_metrics,
    }


def main():
    """Main function for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare slice result with oracle data"
    )
    parser.add_argument(
        "slice_request_id",
        type=str,
        help="The slice request ID (e.g., slice_request_forward_01)",
    )
    parser.add_argument(
        "result_json_path", type=str, help="Path to the result JSON file"
    )
    parser.add_argument(
        "--oracle-dir",
        type=str,
        default=None,
        help="Directory containing oracle files (default: oracle/ in project root)",
    )

    args = parser.parse_args()

    try:
        results = judge_slice_result(
            args.slice_request_id, args.result_json_path, args.oracle_dir
        )

        # Print results
        print(json.dumps(results, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=os.sys.stderr)
        os.sys.exit(1)


if __name__ == "__main__":
    main()
