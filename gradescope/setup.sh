#!/usr/bin/env bash
set -euo pipefail

apt-get update -y
apt-get install -y curl build-essential git

# Install Rust (non-interactive)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"

# Python dependencies
pip3 install pytest

# Pre-warm the Cargo registry so per-submission grading doesn't re-download crates
cargo build --manifest-path /autograder/source/rust_template/Cargo.toml
