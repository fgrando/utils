CC      := gcc
CFLAGS  := -O2 -Wall
LDLIBS  := -lws2_32

SRCS := $(wildcard *.c)
EXES := $(SRCS:.c=.exe)

.PHONY: all clean

all: $(EXES)

%.exe: %.c
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

clean:
	rm -f $(EXES)
