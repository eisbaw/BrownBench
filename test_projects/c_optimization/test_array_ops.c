#include "array_ops.h"
#include <stdio.h>
#include <assert.h>
#include <time.h>

#define ARRAY_SIZE 10000000

void test_correctness() {
    /* Small arrays for correctness */
    int64_t arr1[] = {1, 2, 3, 4, 5};
    assert(array_sum(arr1, 5) == 15);

    int64_t arr2[] = {-5, -4, -3, -2, -1};
    assert(array_sum(arr2, 5) == -15);

    int64_t arr3[] = {0};
    assert(array_sum(arr3, 1) == 0);

    int64_t empty[] = {};
    assert(array_sum(empty, 0) == 0);

    printf("✓ Correctness tests passed\n");
}

void test_performance() {
    /* Large array for performance testing */
    static int64_t arr[ARRAY_SIZE];

    /* Initialize with known values */
    for (int i = 0; i < ARRAY_SIZE; i++) {
        arr[i] = i % 100;
    }

    clock_t start = clock();
    int64_t sum = array_sum(arr, ARRAY_SIZE);
    clock_t end = clock();

    double elapsed = ((double)(end - start)) / CLOCKS_PER_SEC * 1000.0;

    /* Expected sum can be calculated */
    int64_t expected = 0;
    for (int i = 0; i < ARRAY_SIZE; i++) {
        expected += i % 100;
    }

    assert(sum == expected);
    printf("✓ Performance test passed (%.2f ms)\n", elapsed);

    /* Hint: Optimized version should be faster */
    /* Baseline naive: ~10-20ms on modern CPU */
    /* Optimized: <5ms possible with loop unrolling */
}

int main() {
    test_correctness();
    test_performance();
    printf("\nAll tests passed!\n");
    return 0;
}
