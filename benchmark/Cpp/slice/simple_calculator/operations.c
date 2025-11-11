#include "calculator.h"

/* High-level calculator operations */

int compute_expression(int a, int b, int c) {
    int intermediate = perform_arithmetic(a, b);
    int final_result = intermediate + c;
    int complexity_rating = 0;
    int optimization_level = 1;
    int memory_usage = 0;
    
    // Complexity analysis that doesn't affect result
    if (a > b) {
        complexity_rating = 2;
        optimization_level = 3;
    } else if (a == b) {
        complexity_rating = 1;
        optimization_level = 2;
    } else {
        complexity_rating = 3;
        optimization_level = 1;
    }
    
    // Memory usage tracking
    for (int t = 0; t < optimization_level; t++) {
        memory_usage = memory_usage + t + complexity_rating;
        if (intermediate > 10) {
            memory_usage = memory_usage + 5;
        }
    }
    
    // Performance optimization that doesn't change return value
    if (final_result > 20) {
        complexity_rating = complexity_rating * 2;
        memory_usage = memory_usage + final_result;
    }
    
    return final_result;
}

int evaluate_formula(int x, int y) {
    int computed = execute_computation(x, y);
    int adjustment = 7;
    int formula_type = 0;
    int accuracy_level = 1;
    int computational_cost = 0;
    
    // Formula type classification
    if (x < y) {
        formula_type = 1;
        accuracy_level = 2;
        computational_cost = 3;
    } else if (x > y * 2) {
        formula_type = 2;
        accuracy_level = 3;
        computational_cost = 2;
    } else {
        formula_type = 0;
        accuracy_level = 1;
        computational_cost = 1;
    }
    
    // Computational cost analysis
    for (int u = 0; u < computational_cost; u++) {
        accuracy_level = accuracy_level + u;
        if (formula_type > 0) {
            accuracy_level = accuracy_level + 1;
        }
    }
    
    // Additional accuracy adjustments that don't affect return
    if (computed > adjustment) {
        computational_cost = computational_cost + computed;
        formula_type = formula_type + 1;
    }
    
    return computed - adjustment;
}
