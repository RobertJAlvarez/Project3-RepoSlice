#!/bin/bash

# RepoSlice Single Slice Analysis Runner
# This script executes program slicing analysis for a single JSON request file

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
    echo "RepoSlice Single Slice Runner"
    echo "=========================================="
    echo ""
    echo "Usage: $0 <slice_request_path.json> [options]"
    echo ""
    echo "Arguments:"
    echo "  slice_request_path.json    Path to the JSON slice request file"
    echo ""
    echo "Options:"
    echo "  --model <model_name>       LLM model to use (default: gpt-4o-mini)"
    echo "  --workers <num>            Max symbolic workers (default: 5)"
    echo "  --queries <num>            Max queries to LLM (default: 10)"
    echo "  --temp <float>             Temperature (default: 0.5)"
    echo "  --depth <num>              Call depth (default: 3)"
    echo "  --help, -h                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 ../benchmark/Cpp/slice/slice_request_forward_01.json"
    echo "  $0 ../benchmark/Cpp/slice/slice_request_backward_01.json --model gpt-4o --workers 10"
    echo ""
}

# Default parameters
MODEL="gpt-4o-mini"
MAX_SYMBOLIC_WORKERS=10
MAX_QUERIES=20
TEMPERATURE=0.0
CALL_DEPTH=10
SLICE_REQUEST_PATH=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_usage
            exit 0
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --workers)
            MAX_SYMBOLIC_WORKERS="$2"
            shift 2
            ;;
        --queries)
            MAX_QUERIES="$2"
            shift 2
            ;;
        --temp)
            TEMPERATURE="$2"
            shift 2
            ;;
        --depth)
            CALL_DEPTH="$2"
            shift 2
            ;;
        *.json)
            SLICE_REQUEST_PATH="$1"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$SLICE_REQUEST_PATH" ]; then
    print_error "Missing required argument: slice_request_path.json"
    echo ""
    show_usage
    exit 1
fi

# Check if file exists
if [ ! -f "$SLICE_REQUEST_PATH" ]; then
    print_error "Slice request file not found: $SLICE_REQUEST_PATH"
    exit 1
fi

# Header
echo "=========================================="
echo "RepoSlice: Run inter-procedural program slicer"
echo "=========================================="

# Check if conda environment should be activated
if command -v conda &> /dev/null; then
    print_info "Activating conda environment 'reposlice'..."
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate reposlice
fi

# Display configuration
print_info "Configuration:"
echo "  Request file: $SLICE_REQUEST_PATH"
echo "  Model: $MODEL"
echo "  Symbolic workers: $MAX_SYMBOLIC_WORKERS"
echo "  Max queries: $MAX_QUERIES"
echo "  Temperature: $TEMPERATURE"
echo "  Call depth: $CALL_DEPTH"
echo ""

# Extract request info for display
if command -v jq &> /dev/null; then
    SEED_NAME=$(jq -r '.seed_name' "$SLICE_REQUEST_PATH" 2>/dev/null || echo "unknown")
    IS_BACKWARD=$(jq -r '.is_backward' "$SLICE_REQUEST_PATH" 2>/dev/null || echo "unknown")
    SLICE_TYPE=$([ "$IS_BACKWARD" = "true" ] && echo "Backward" || echo "Forward")
    print_info "Slice type: $SLICE_TYPE slice for variable '$SEED_NAME'"
fi

# Start analysis
print_info "Starting slice analysis..."
start_time=$(date)

# Run the slicing analysis
python reposlice.py \
    --slice-request-path "$SLICE_REQUEST_PATH" \
    --language Cpp \
    --max-symbolic-workers "$MAX_SYMBOLIC_WORKERS" \
    --max-query-num "$MAX_QUERIES" \
    --audit-model-name "$MODEL" \
    --temperature "$TEMPERATURE" \
    --call-depth "$CALL_DEPTH"

# Check exit status
if [ $? -eq 0 ]; then
    end_time=$(date)
    print_success "Analysis completed successfully!"
    echo ""
    echo "Started at:  $start_time"
    echo "Finished at: $end_time"
    echo ""
    print_info "Results are available in:"
    echo "  - Log files: ../log/SliceScanAgent/"
    echo "  - Result files: ../result/SliceScanAgent/"
    echo ""
    print_info "To view the latest result:"
    echo "  find ../result/SliceScanAgent/ -name 'slice_info*.json' -type f -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2- | xargs cat | jq ."
else
    print_error "Analysis failed!"
    exit 1
fi
