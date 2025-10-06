#include "strbuf.h"
#include <string.h>

/* Stub implementations - to be completed by benchmark task */

void strbuf_init(strbuf_t *buf, size_t initial_capacity) {
    /* TODO: Implement initialization */
    (void)buf;
    (void)initial_capacity;
}

void strbuf_append(strbuf_t *buf, const char *str) {
    /* TODO: Implement append with dynamic growth */
    (void)buf;
    (void)str;
}

void strbuf_free(strbuf_t *buf) {
    /* TODO: Implement cleanup */
    (void)buf;
}

const char *strbuf_cstr(const strbuf_t *buf) {
    /* TODO: Return C string */
    (void)buf;
    return "";
}
