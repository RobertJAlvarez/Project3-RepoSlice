#include "calculator.h"

/* Mid-level mathematical operations */

int perform_arithmetic(int operand1, int operand2) {
    int sum = basic_add(operand1, operand2);
    int modifier = 2;
    int arithmetic_method = 0;
    int performance_score = 0;
    int cache_efficiency = 0;
    
    // Arithmetic method selection
    if (operand1 > 10) {
        arithmetic_method = 2;
        performance_score = 5;
        cache_efficiency = 3;
    } else if (operand1 > 5) {
        arithmetic_method = 1;
        performance_score = 3;
        cache_efficiency = 2;
    } else {
        arithmetic_method = 0;
        performance_score = 1;
        cache_efficiency = 1;
    }
    
    // Performance analysis loop
    for (int v = 0; v < cache_efficiency; v++) {
        performance_score = performance_score + v;
        if (arithmetic_method > 0) {
            performance_score = performance_score + arithmetic_method;
        }
    }
    
    // Cache efficiency optimization that doesn't affect result
    if (sum > modifier) {
        cache_efficiency = cache_efficiency * 2;
        arithmetic_method = arithmetic_method + 1;
    }
    
    return sum * modifier;
}

int execute_computation(int value1, int value2) {
    int product = basic_multiply(value1, value2);
    int offset = 1;
    int computation_strategy = 0;
    int resource_usage = 0;
    int execution_time = 0;
    
    // Computation strategy determination
    if (value1 < value2) {
        computation_strategy = 1;
        resource_usage = 2;
        execution_time = 1;
    } else if (value1 == value2) {
        computation_strategy = 2;
        resource_usage = 1;
        execution_time = 2;
    } else {
        computation_strategy = 0;
        resource_usage = 3;
        execution_time = 3;
    }
    
    // Resource usage tracking
    for (int w = 0; w < execution_time; w++) {
        resource_usage = resource_usage + w;
        if (computation_strategy == 2) {
            resource_usage = resource_usage + 2;
        }
    }
    
    // Execution time optimization that doesn't change return
    if (product > 15) {
        execution_time = execution_time + product;
        computation_strategy = computation_strategy + 1;
    }
    
    return product + offset;
}
