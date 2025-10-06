{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python 3.12
    python312
    python312Packages.pip

    # uv for fast package management
    uv

    # Just for task running
    just

    # Linting and type checking (use nix versions to avoid dynamic linking issues)
    ruff
    python312Packages.mypy

    # Development tools
    git
    gnumake

    # Optional: For building reference projects
    gcc
    clang
  ];

  shellHook = ''
    if [ ! -d .venv ]; then
      uv venv .venv
    fi
    source .venv/bin/activate
    uv pip install -e ".[dev]"
    export CODEGEN_BENCH_DEV=1
  '';
}
