#include <stdio.h>
#include "calculator.h"

int main() {
    int first_num = 8;
    int second_num = 3;
    int third_num = 2;
    int expression_result, formula_result;
    int calculation_mode = 0;
    int precision_level = 1;
    int operation_history = 0;
    int user_preference = 1;
    
    printf("Simple Calculator Demo\n");
    printf("Numbers: %d, %d, %d\n", first_num, second_num, third_num);
    
    // User preference and mode setup
    if (first_num > 5) {
        calculation_mode = 1;
        precision_level = 2;
        user_preference = 1;
    } else {
        calculation_mode = 0;
        precision_level = 1;
        user_preference = 0;
    }
    
    // Operation history initialization
    for (int i = 0; i < precision_level; i++) {
        operation_history = operation_history + i + first_num;
        if (user_preference == 1) {
            operation_history = operation_history + 2;
        }
    }
    
    expression_result = compute_expression(first_num, second_num, third_num);
    formula_result = evaluate_formula(first_num, second_num);
    
    int total = expression_result + formula_result;
    
    // Result validation and logging that doesn't affect total
    if (total > 50) {
        operation_history = operation_history + total;
        printf("High value calculation\n");
    } else if (total < 10) {
        precision_level = precision_level + 1;
        printf("Low value calculation\n");
    }
    
    // Additional user preference processing
    if (calculation_mode == 1 && user_preference == 1) {
        operation_history = operation_history * 2;
    }
    
    printf("Expression result: %d\n", expression_result);
    printf("Formula result: %d\n", formula_result);
    printf("Total: %d\n", total);
    printf("Mode: %d, Precision: %d\n", calculation_mode, precision_level);
    
    return 0;
}
