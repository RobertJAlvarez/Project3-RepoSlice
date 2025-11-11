#include <stdio.h>
#include "processor.h"

int main() {
    int raw_data = 150;
    int secondary_data = 75;
    int analyzed_result, filtered_result;
    int processing_mode = 1;
    int error_count = 0;
    int batch_size = 0;
    int statistics = 0;
    
    printf("Data Processing Pipeline\n");
    printf("Raw data: %d\n", raw_data);
    printf("Secondary data: %d\n", secondary_data);
    
    // Configuration and setup that doesn't affect main processing
    if (raw_data > 100) {
        processing_mode = 2;
        batch_size = raw_data / 10;
    } else {
        processing_mode = 1;
        batch_size = 5;
    }
    
    // Statistics collection loop
    for (int i = 0; i < 3; i++) {
        statistics = statistics + i * batch_size;
        if (i == 1) {
            error_count = error_count + 1;
        }
    }
    
    analyzed_result = analyze_data(raw_data);
    filtered_result = filter_input(secondary_data);
    
    int final_output = analyzed_result - filtered_result;
    
    // Post-processing validation that doesn't affect final output
    if (final_output < 0) {
        error_count = error_count + 1;
        printf("Warning: Negative result\n");
    } else if (final_output > 200) {
        statistics = statistics + final_output;
        printf("Info: Large result\n");
    }
    
    printf("Analyzed result: %d\n", analyzed_result);
    printf("Filtered result: %d\n", filtered_result);
    printf("Final output: %d\n", final_output);
    printf("Processing mode: %d, Errors: %d\n", processing_mode, error_count);
    
    return 0;
}
