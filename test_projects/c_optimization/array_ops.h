#ifndef ARRAY_OPS_H
#define ARRAY_OPS_H

#include <stddef.h>
#include <stdint.h>

/**
 * Sum an array of 64-bit integers.
 * Current implementation is naive - can be optimized.
 *
 * @param arr Array of int64_t values
 * @param len Number of elements
 * @return Sum of all elements
 */
int64_t array_sum(const int64_t *arr, size_t len);

#endif /* ARRAY_OPS_H */
