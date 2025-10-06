CC = gcc
CFLAGS = -Wall -Wextra -Werror -std=c99

all: test_strbuf

test_strbuf: test_strbuf.o strbuf.o
	$(CC) $(CFLAGS) -o test_strbuf test_strbuf.o strbuf.o

test_strbuf.o: test_strbuf.c strbuf.h
	$(CC) $(CFLAGS) -c test_strbuf.c

strbuf.o: strbuf.c strbuf.h
	$(CC) $(CFLAGS) -c strbuf.c

clean:
	rm -f *.o test_strbuf

test: test_strbuf
	./test_strbuf

.PHONY: all clean test
