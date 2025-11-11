#!/bin/bash

# RepoSlice: Run All Slice Requests
# This script executes slicing analysis for all six JSON request files provided in the benchmark/Cpp/slice directory.

echo "=========================================="
echo "RepoSlice: Running All Slice Requests"
echo "=========================================="

# Set paths
SLICE_DIR="../benchmark/Cpp/slice"
PYTHON_CMD="python"

# Check if conda environment should be activated
if command -v conda &> /dev/null; then
    echo "Activating conda environment 'reposlice'..."
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate reposlice
fi

# Function to run slice analysis
run_slice_analysis() {
    local request_file="$1"
    local description="$2"
    local counter="$3"
    
    echo ""
    echo "[$counter/6] ================================"
    echo "Running: $description"
    echo "Request file: $request_file"
    echo "================================"
    
    if [ ! -f "$SLICE_DIR/$request_file" ]; then
        echo "❌ Error: Request file '$request_file' not found!"
        return 1
    fi
    
    # Run the slicing analysis
    $PYTHON_CMD reposlice.py \
        --slice-request-path "$SLICE_DIR/$request_file" \
        --language "Cpp" \
        --max-symbolic-workers 10 \
        --max-query-num 20 \
        --audit-model-name "gpt-4o-mini" \
        --temperature 0.0 \
        --call-depth 10
    
    if [ $? -eq 0 ]; then
        echo "✅ Analysis completed successfully: $description"
    else
        echo "❌ Analysis failed: $description"
    fi
    
    echo ""
    sleep 2  # Brief pause between analyses
}

# Start timestamp
start_time=$(date)
echo "Started at: $start_time"
echo ""

# Run all six slice analyses
echo "Executing slice analyses for all projects..."

# Arithmetic Chain Project  
# run_slice_analysis "slice_request_backward_01.json" 
run_slice_analysis "slice_request_forward_01.json"

# # Data Processing Project
# run_slice_analysis "slice_request_backward_02.json" 
# run_slice_analysis "slice_request_forward_02.json"

# # Simple Calculator Project
# run_slice_analysis "slice_request_backward_03.json" 
# run_slice_analysis "slice_request_forward_03.json"


# End timestamp and summary
end_time=$(date)
echo "=========================================="
echo "All slice analyses completed!"
echo "Started at:  $start_time"
echo "Finished at: $end_time"
echo "=========================================="

echo ""
echo "Results are available in:"
echo "- Log files: ../log/SliceScanAgent/"
echo "- Result files: ../result/SliceScanAgent/"
echo ""

echo "To view results:"
echo "  ls -la ../log/SliceScanAgent/"
echo "  ls -la ../result/SliceScanAgent/"
echo ""

echo "To analyze a specific result:"
echo "  find ../result/SliceScanAgent/ -name 'slice_info*.json' | head -1 | xargs cat"
