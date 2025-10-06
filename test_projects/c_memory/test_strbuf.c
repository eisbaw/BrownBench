#include "strbuf.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

void test_basic_init_and_free() {
    strbuf_t buf;
    strbuf_init(&buf, 16);
    assert(buf.data != NULL);
    assert(buf.len == 0);
    assert(buf.capacity >= 16);
    strbuf_free(&buf);
    printf("✓ test_basic_init_and_free\n");
}

void test_append_single() {
    strbuf_t buf;
    strbuf_init(&buf, 16);
    strbuf_append(&buf, "hello");
    assert(strcmp(strbuf_cstr(&buf), "hello") == 0);
    assert(buf.len == 5);
    strbuf_free(&buf);
    printf("✓ test_append_single\n");
}

void test_append_multiple() {
    strbuf_t buf;
    strbuf_init(&buf, 16);
    strbuf_append(&buf, "hello");
    strbuf_append(&buf, " ");
    strbuf_append(&buf, "world");
    assert(strcmp(strbuf_cstr(&buf), "hello world") == 0);
    assert(buf.len == 11);
    strbuf_free(&buf);
    printf("✓ test_append_multiple\n");
}

void test_dynamic_growth() {
    strbuf_t buf;
    strbuf_init(&buf, 4); /* Small initial capacity */
    strbuf_append(&buf, "This is a longer string that needs reallocation");
    assert(strcmp(strbuf_cstr(&buf),
           "This is a longer string that needs reallocation") == 0);
    assert(buf.capacity > 4);
    strbuf_free(&buf);
    printf("✓ test_dynamic_growth\n");
}

void test_empty_string() {
    strbuf_t buf;
    strbuf_init(&buf, 16);
    assert(strcmp(strbuf_cstr(&buf), "") == 0);
    strbuf_free(&buf);
    printf("✓ test_empty_string\n");
}

int main() {
    test_basic_init_and_free();
    test_append_single();
    test_append_multiple();
    test_dynamic_growth();
    test_empty_string();
    printf("\nAll tests passed!\n");
    return 0;
}
