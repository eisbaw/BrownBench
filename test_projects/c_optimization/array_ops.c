#include "array_ops.h"

/**
 * Naive implementation with potential optimizations:
 * - Loop unrolling
 * - Multiple accumulators to reduce dependency chains
 * - Better compiler hints
 */
int64_t array_sum(const int64_t *arr, size_t len) {
    int64_t sum = 0;
    for (size_t i = 0; i < len; i++) {
        sum += arr[i];
    }
    return sum;
}
