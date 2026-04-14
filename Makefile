CC      = clang
TARGET  = twin_peaks

SRC_DIR = src
INC_DIR = include

SRCS    = $(wildcard $(SRC_DIR)/*.c)
OBJS    = $(SRCS:$(SRC_DIR)/%.c=build/%.o)

CFLAGS  = -Wall -Wextra -Wpedantic -std=c11 -I$(INC_DIR)
CFLAGS += $(shell sdl2-config --cflags)

LDFLAGS = $(shell sdl2-config --libs) -lm

# Debug build (default)
.PHONY: all
all: CFLAGS += -g -O0 -DDEBUG
all: $(TARGET)

# Release build
.PHONY: release
release: CFLAGS += -O2 -DNDEBUG
release: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

build/%.o: $(SRC_DIR)/%.c
	@mkdir -p build
	$(CC) $(CFLAGS) -c $< -o $@

.PHONY: clean
clean:
	rm -rf build $(TARGET)

.PHONY: run
run: all
	./$(TARGET)