#include "processor.h"

/* Main analysis functions */

int analyze_data(int data_value) {
    int validated = validate_range(data_value);
    int offset = 10;
    int quality_score = 0;
    int processing_time = 0;
    int metadata = 0;
    
    // Quality assessment that doesn't affect main result
    if (data_value > 120) {
        quality_score = 5;
        processing_time = 3;
    } else if (data_value > 80) {
        quality_score = 3;
        processing_time = 2;
    } else {
        quality_score = 1;
        processing_time = 1;
    }
    
    // Metadata collection loop
    for (int m = 0; m < processing_time; m++) {
        metadata = metadata + m + quality_score;
    }
    
    // Additional validation that doesn't change return value
    if (validated > 100) {
        quality_score = quality_score * 2;
        metadata = metadata + validated;
    }
    
    return validated + offset;
}

int filter_input(int input) {
    int normalized = normalize_value(input);
    int threshold = 50;
    int filter_level = 1;
    int cache_hit = 0;
    int performance_metric = 0;
    
    // Filter level determination
    if (input < 30) {
        filter_level = 3;
        cache_hit = 0;
    } else if (input < 60) {
        filter_level = 2;
        cache_hit = 1;
    } else {
        filter_level = 1;
        cache_hit = 1;
    }
    
    // Performance tracking
    performance_metric = filter_level * cache_hit;
    for (int n = 0; n < filter_level; n++) {
        performance_metric = performance_metric + n;
    }
    
    if (normalized > threshold) {
        // Additional processing in this branch
        if (cache_hit) {
            performance_metric = performance_metric + 5;
        }
        return normalized - threshold;
    } else {
        // Different processing in this branch
        performance_metric = performance_metric + filter_level;
        return normalized;
    }
}
