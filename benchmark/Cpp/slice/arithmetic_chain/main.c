#include <stdio.h>

int main() {
    int input_a = 10;
    int input_b = 5;
    int debug_flag = 1;
    int result1, result2, final_result;
    int temp_var = 0;
    int unused_calculation = 0;
    
    printf("Starting arithmetic chain calculation\n");
    printf("Input values: a=%d, b=%d\n", input_a, input_b);
    
    unused_calculation = input_a * 3;
    temp_var = input_b - 2;
    
    if (debug_flag) {
        printf("Debug mode enabled\n");
        temp_var = temp_var + 1;
    }

    result1 = input_a * input_b;
    result2 = input_a + input_b;
    
    final_result = result1 + result2;
    
    if (result1 > 20) {
        unused_calculation = unused_calculation + result1;
        printf("Large result detected\n");
    }
    
    printf("Final result: %d\n", final_result);
    printf("Debug info: temp_var=%d\n", temp_var);
    
    return 0;
}
