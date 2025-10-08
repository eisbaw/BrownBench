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

    # C++ standard library and other libs for numpy/scipy
    stdenv.cc.cc.lib
    zlib
  ];

  shellHook = ''
    if [ ! -d .venv ]; then
      uv venv .venv > /dev/null 2>&1
    fi
    source .venv/bin/activate
    uv pip install -e ".[dev]" > /dev/null 2>&1
    export CODEGEN_BENCH_DEV=1
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.zlib}/lib:$LD_LIBRARY_PATH"
    # Unset PYTHONPATH to avoid conflicts between nix and venv packages
    unset PYTHONPATH
  '';
}
