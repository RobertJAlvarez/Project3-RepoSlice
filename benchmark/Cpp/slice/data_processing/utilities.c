#include "processor.h"

/* Core utility functions - deepest level */

int check_bounds(int value) {
    int min_value = 0;
    int max_value = 200;
    int boundary_violations = 0;
    int correction_applied = 0;
    int security_check = 0;
    
    // Security and boundary violation tracking
    if (value < -1000 || value > 1000) {
        security_check = 1;
        boundary_violations = 2;
    } else if (value < min_value || value > max_value) {
        security_check = 0;
        boundary_violations = 1;
    } else {
        security_check = 0;
        boundary_violations = 0;
    }
    
    // Logging and correction tracking
    if (value < min_value) {
        correction_applied = min_value - value;
        for (int r = 0; r < 2; r++) {
            boundary_violations = boundary_violations + r;
        }
        return min_value;
    } else if (value > max_value) {
        correction_applied = value - max_value;
        security_check = security_check + correction_applied;
        return max_value;
    } else {
        correction_applied = 0;
        if (security_check == 0) {
            boundary_violations = boundary_violations + 1;
        }
        return value;
    }
}

int apply_scaling(int value) {
    int scale_factor = 2;
    int scaling_method = 1;
    int efficiency_rating = 0;
    int operation_count = 0;
    
    // Scaling method selection
    if (value > 100) {
        scaling_method = 2;
        efficiency_rating = 3;
        operation_count = 1;
    } else if (value > 50) {
        scaling_method = 1;
        efficiency_rating = 2;
        operation_count = 2;
    } else {
        scaling_method = 1;
        efficiency_rating = 1;
        operation_count = 3;
    }
    
    int scaled = value / scale_factor;
    
    // Efficiency tracking and optimization
    for (int s = 0; s < operation_count; s++) {
        efficiency_rating = efficiency_rating + s;
        if (scaling_method == 2) {
            efficiency_rating = efficiency_rating + 1;
        }
    }
    
    // Additional optimization that doesn't affect result
    if (efficiency_rating > 5) {
        scaling_method = scaling_method + 1;
        operation_count = operation_count - 1;
    }
    
    return scaled + 1;
}
