#!/bin/bash

# RepoSlice: Slice Result Judger
# This script compares slice results with oracle data to calculate precision, recall, and F1 scores

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to show usage
show_usage() {
    echo "=========================================="
    echo "RepoSlice: Slice Result Judger"
    echo "=========================================="
    echo ""
    echo "Usage: $0 <slice_request_id> <result_json_path> [options]"
    echo ""
    echo "Arguments:"
    echo "  slice_request_id        The slice request ID (e.g., slice_request_forward_01)"
    echo "  result_json_path          Path to the result JSON file to judge"
    echo ""
    echo "Options:"
    echo "  --oracle-dir <path>       Directory containing oracle files (default: ../oracle)"
    echo "  --help, -h                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 slice_request_forward_01 path_to_result_json.json"
    echo ""
}

# Default parameters
SLICE_REQUEST_ID=""
RESULT_JSON_PATH=""
ORACLE_DIR=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_usage
            exit 0
            ;;
        --oracle-dir)
            ORACLE_DIR="$2"
            shift 2
            ;;
        *)
            if [ -z "$SLICE_REQUEST_ID" ]; then
                SLICE_REQUEST_ID="$1"
            elif [ -z "$RESULT_JSON_PATH" ]; then
                RESULT_JSON_PATH="$1"
            else
                print_error "Unknown argument: $1"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [ -z "$SLICE_REQUEST_ID" ]; then
    print_error "Missing required argument: slice_request_id"
    echo ""
    show_usage
    exit 1
fi

if [ -z "$RESULT_JSON_PATH" ]; then
    print_error "Missing required argument: result_json_path"
    echo ""
    show_usage
    exit 1
fi

# Check if result file exists
if [ ! -f "$RESULT_JSON_PATH" ]; then
    print_error "Result file not found: $RESULT_JSON_PATH"
    exit 1
fi

# Header
echo "=========================================="
echo "RepoSlice: Slice Result Judger"
echo "=========================================="

# Check if conda environment should be activated
if command -v conda &> /dev/null; then
    print_info "Activating conda environment 'reposlice'..."
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate reposlice
fi

# Display configuration
print_info "Configuration:"
echo "  Slice request ID: $SLICE_REQUEST_ID"
echo "  Result file: $RESULT_JSON_PATH"
if [ -n "$ORACLE_DIR" ]; then
    echo "  Oracle directory: $ORACLE_DIR"
else
    echo "  Oracle directory: ../oracle (default)"
fi
echo ""

# Check if oracle file exists
if [ -n "$ORACLE_DIR" ]; then
    ORACLE_PATH="$ORACLE_DIR/${SLICE_REQUEST_ID}.json"
else
    ORACLE_PATH="../oracle/${SLICE_REQUEST_ID}.json"
fi

if [ ! -f "$ORACLE_PATH" ]; then
    print_error "Oracle file not found: $ORACLE_PATH"
    print_info "Available oracle files:"
    if [ -n "$ORACLE_DIR" ]; then
        ls -1 "$ORACLE_DIR"/*.json 2>/dev/null | xargs -n1 basename || echo "  (none found)"
    else
        ls -1 ../oracle/*.json 2>/dev/null | xargs -n1 basename || echo "  (none found)"
    fi
    exit 1
fi

print_info "Oracle file found: $ORACLE_PATH"
echo ""

# Start judging
print_info "Starting judgment..."
start_time=$(date)

# Build command
JUDGE_CMD="python utility/judger.py \"$SLICE_REQUEST_ID\" \"$RESULT_JSON_PATH\""
if [ -n "$ORACLE_DIR" ]; then
    JUDGE_CMD="$JUDGE_CMD --oracle-dir \"$ORACLE_DIR\""
fi

# Run the judger
eval $JUDGE_CMD

# Check exit status
if [ $? -eq 0 ]; then
    end_time=$(date)
    echo ""
    print_success "Judgment completed successfully!"
    echo ""
    echo "Started at:  $start_time"
    echo "Finished at: $end_time"
else
    print_error "Judgment failed!"
    exit 1
fi

