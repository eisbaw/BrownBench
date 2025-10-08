# Build and Test Commands for Source Repositories

This document contains the build and test commands for each repository used in BrownBench task curation.

## C/C++ Projects

### Git
**Repository**: submodules/git
**Language**: C
**Build System**: Make

```bash
# Build
make

# Test (full suite - takes ~30 minutes)
make test

# Test (specific test)
cd t && ./t0001-init.sh

# Fast smoke test
make test T=t0000-basic.sh
```

**Notes**:
- Requires: gcc, make, perl, shell utils
- Tests are in `t/` directory
- Can be slow - individual tests recommended

### Redis
**Repository**: submodules/redis
**Language**: C
**Build System**: Make

```bash
# Build
make

# Test (full suite)
make test

# Test (specific module)
./runtest --single unit/type/string

# Quick smoke test
make test TAGS="-psync"
```

**Notes**:
- Requires: gcc, make, tcl
- Tests use TCL framework
- Fast builds, moderate test time

### nginx
**Repository**: submodules/nginx
**Language**: C
**Build System**: Configure + Make

```bash
# Configure and build
./auto/configure
make

# Test (if test suite available)
make test

# Manual verification
objs/nginx -t
```

**Notes**:
- Requires: gcc, make, pcre, zlib, openssl
- Limited automated tests
- Primarily manual testing
- May need to skip for benchmark (no reliable test suite)

### SQLite
**Repository**: submodules/sqlite
**Language**: C
**Build System**: Configure + Make

```bash
# Configure and build
./configure
make

# Test (full suite - very comprehensive)
make test

# Quick test
make quicktest

# Specific test
make fuzztest
```

**Notes**:
- Requires: gcc, make, tcl
- Extensive test suite (very thorough)
- Tests can be slow
- Well-suited for benchmarking

### curl/libcurl
**Repository**: submodules/curl
**Language**: C
**Build System**: CMake or Autotools

```bash
# Autotools approach
./buildconf
./configure
make

# CMake approach
mkdir build && cd build
cmake ..
make

# Test
make test
```

**Notes**:
- Requires: gcc/clang, make, cmake or autotools
- Good test coverage
- Tests involve network mocking
- Well-suited for benchmarking

### OpenSSH
**Repository**: submodules/openssh
**Language**: C
**Build System**: Autotools

```bash
# Configure and build
autoreconf
./configure
make

# Test
make tests

# Regression tests
cd regress && make
```

**Notes**:
- Requires: gcc, openssl, zlib
- Comprehensive regression tests
- Tests can be complex (requires setup)

### HAProxy
**Repository**: submodules/haproxy
**Language**: C
**Build System**: Make

```bash
# Build
make TARGET=linux-glibc

# Test (if available)
make reg-tests

# Unit tests
make test
```

**Notes**:
- Requires: gcc, make
- TARGET must be specified
- Good test coverage

### tmux
**Repository**: submodules/tmux
**Language**: C
**Build System**: Autotools

```bash
# Build
./autogen.sh
./configure
make

# Test (limited automated tests)
make check
```

**Notes**:
- Requires: gcc, libevent, ncurses
- Limited automated tests
- Primarily manual testing

### jq
**Repository**: submodules/jq
**Language**: C
**Build System**: Autotools

```bash
# Build
autoreconf -i
./configure
make

# Test
make check

# Specific tests
cd tests && ./run
```

**Notes**:
- Requires: gcc, make, autotools
- Good test coverage
- Tests are bash scripts
- Well-suited for benchmarking

### zstd
**Repository**: submodules/zstd
**Language**: C
**Build System**: Make

```bash
# Build
make

# Test
make test

# Quick test
make shortest

# All tests
make alltest
```

**Notes**:
- Requires: gcc, make
- Excellent test coverage
- Fast builds and tests
- Very well-suited for benchmarking

## Go Projects

### containerd
**Repository**: submodules/containerd
**Language**: Go
**Build System**: Make (wrapping Go)

```bash
# Build
make

# Test (all)
make test

# Test (specific package)
go test ./pkg/cri/...

# Integration tests
make integration
```

**Notes**:
- Requires: Go 1.20+, make
- Good test coverage
- Integration tests may require docker

### etcd
**Repository**: submodules/etcd
**Language**: Go
**Build System**: Make (wrapping Go)

```bash
# Build
make build

# Test (unit tests)
make test

# Test (integration)
make test-integration

# Fast unit tests
go test -short ./...
```

**Notes**:
- Requires: Go 1.20+
- Comprehensive tests
- Integration tests can be slow

## Rust Projects

### ripgrep
**Repository**: submodules/ripgrep
**Language**: Rust
**Build System**: Cargo

```bash
# Build
cargo build

# Test
cargo test

# Test (specific)
cargo test --test tests

# Quick test
cargo test --lib
```

**Notes**:
- Requires: Rust/Cargo
- Excellent test coverage
- Fast builds and tests
- Very well-suited for benchmarking

## Project Selection for Tasks

Based on test suite quality and build reliability:

**Highly Recommended** (good test coverage, reliable builds):
1. zstd - Excellent tests, fast builds
2. ripgrep - Excellent tests, fast builds
3. jq - Good tests, straightforward
4. Redis - Good tests, fast builds
5. SQLite - Excellent tests (but slow)

**Recommended** (good but with caveats):
1. curl - Good tests, some network complexity
2. Git - Good tests, but slow
3. etcd - Good tests, Go ecosystem
4. containerd - Good tests, may need docker

**Use with Caution** (limited or complex testing):
1. OpenSSH - Complex setup for tests
2. HAProxy - Limited automated tests
3. nginx - Limited automated tests
4. tmux - Limited automated tests

## Testing Strategy for Task Validation

For creating benchmark tasks, prioritize projects where:
1. Build is deterministic and fast
2. Tests are comprehensive and automated
3. No external dependencies (databases, networks)
4. Tests complete in reasonable time (<5 min)

Ideal candidates: **zstd, ripgrep, jq, Redis**
