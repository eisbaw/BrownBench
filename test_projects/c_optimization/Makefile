CC = gcc
CFLAGS = -Wall -Wextra -Werror -std=c99 -O2

all: test_array_ops

test_array_ops: test_array_ops.o array_ops.o
	$(CC) $(CFLAGS) -o test_array_ops test_array_ops.o array_ops.o

test_array_ops.o: test_array_ops.c array_ops.h
	$(CC) $(CFLAGS) -c test_array_ops.c

array_ops.o: array_ops.c array_ops.h
	$(CC) $(CFLAGS) -c array_ops.c

clean:
	rm -f *.o test_array_ops

test: test_array_ops
	./test_array_ops

.PHONY: all clean test
