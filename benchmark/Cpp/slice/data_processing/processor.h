#ifndef PROCESSOR_H
#define PROCESSOR_H

/* Main processing functions */
int analyze_data(int data_value);
int filter_input(int input);

/* Intermediate processing functions */
int validate_range(int value);
int normalize_value(int raw_value);

/* Core utility functions */
int check_bounds(int value);
int apply_scaling(int value);

#endif
