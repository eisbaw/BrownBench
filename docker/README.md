# Docker Container Isolation for BrownBench

This directory contains Dockerfiles and configuration for running DUTs (Device Under Test) in isolated containers.

## Overview

Container isolation provides:
- **Network restrictions**: Only API proxy access allowed
- **Resource limits**: CPU, memory, and timeout controls
- **Read-only mounts**: Prevent filesystem modifications
- **Automatic cleanup**: Containers removed after execution

## Building the DUT Image

Build the default Python DUT image:

```bash
docker build -t brownbench-dut:latest -f docker/Dockerfile.dut .
```

Build with a specific Python version:

```bash
docker build \
  --build-arg PYTHON_VERSION=3.12 \
  -t brownbench-dut:py312 \
  -f docker/Dockerfile.dut .
```

## Using Container Isolation

Example usage in Python:

```python
from codegen_bench.security import (
    ContainerConfig,
    ContainerIsolation,
    ResourceLimits,
    NetworkConfig,
)

# Configure resource limits
resources = ResourceLimits(
    cpu_count=1.0,        # 1 CPU core
    memory_mb=512,        # 512 MB RAM
    timeout_seconds=300,  # 5 minute timeout
)

# Configure network (disabled by default for security)
network = NetworkConfig(
    enabled=False,  # No network access
)

# Create container configuration
config = ContainerConfig(
    image="brownbench-dut:latest",
    resources=resources,
    network=network,
    work_dir="/workspace",
)

# Initialize isolation
isolation = ContainerIsolation(config)

# Execute code in isolated container
result = isolation.execute(
    command=["python", "my_script.py"],
    env={"API_KEY": "temp-key-123"},
)

print(f"Exit code: {result.returncode}")
print(f"Output: {result.stdout}")
```

## Network Proxy Configuration

To allow API access through a proxy:

```python
from codegen_bench.security import NetworkConfig

network = NetworkConfig(
    enabled=True,
    proxy_host="localhost",
    proxy_port=8080,
)

config = ContainerConfig(
    image="brownbench-dut:latest",
    network=network,
)
```

This configures HTTP_PROXY and HTTPS_PROXY environment variables to route traffic through the specified proxy.

## Cleanup

Remove all DUT images:

```bash
docker images | grep brownbench-dut | awk '{print $3}' | xargs docker rmi
```

Or use the programmatic API:

```python
isolation.cleanup_image()
isolation.cleanup_containers(label="app=brownbench")
```

## Security Considerations

1. **Always use resource limits** to prevent runaway processes
2. **Disable network** unless API access is required
3. **Use read-only mounts** for code repositories
4. **Run as non-root user** (already configured in Dockerfile.dut)
5. **Clean up containers** after execution

## Troubleshooting

### Docker not available

Ensure Docker is installed and running:

```bash
docker version
```

### Permission denied

Add your user to the docker group:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Out of memory errors

Increase memory limit in ContainerConfig:

```python
resources = ResourceLimits(memory_mb=1024)  # 1 GB
```

### Build timeout

The default build timeout is 300 seconds. For slow networks, this may need adjustment in the isolation.py code.
