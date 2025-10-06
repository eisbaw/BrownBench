#ifndef STRBUF_H
#define STRBUF_H

#include <stddef.h>

/**
 * Dynamic string buffer
 */
typedef struct {
    char *data;
    size_t len;
    size_t capacity;
} strbuf_t;

/**
 * Initialize a string buffer
 */
void strbuf_init(strbuf_t *buf, size_t initial_capacity);

/**
 * Append a string to the buffer
 */
void strbuf_append(strbuf_t *buf, const char *str);

/**
 * Free the buffer
 */
void strbuf_free(strbuf_t *buf);

/**
 * Get the C string
 */
const char *strbuf_cstr(const strbuf_t *buf);

#endif /* STRBUF_H */
