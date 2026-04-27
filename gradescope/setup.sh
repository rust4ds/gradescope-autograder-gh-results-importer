#!/usr/bin/env bash
set -euo pipefail

apt-get update -y
apt-get install -y curl build-essential git

# Install Rust (non-interactive) with stable as the bootstrap toolchain.
# The rust_template's rust-toolchain.toml then pins the exact version + components
# (rustfmt, clippy), and rustup auto-installs that toolchain on first `cargo` run.
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"

# Pre-warm the Cargo registry so per-submission grading doesn't re-download crates
# rust_template/ is placed at the source root by make_zip.sh
cargo build --manifest-path /autograder/source/rust_template/Cargo.toml

# Wrap the git binary so Gradescope's own clone call is intercepted.
# When Gradescope clones the student repo into /autograder/submission/,
# the wrapper saves the URL (with embedded OAuth token) to a temp file.
# run_autograder then re-clones with full depth using that URL so we get
# complete commit history and all remote branches for grading.
REAL_GIT=$(which git)
cat > /usr/local/bin/git << WRAPPER
#!/bin/bash
if [ "\$1" = "clone" ]; then
    for arg in "\$@"; do
        case "\$arg" in
            https://*github.com*)
                echo "\$arg" > /tmp/gradescope_repo_url.txt
                chmod 600 /tmp/gradescope_repo_url.txt
                ;;
        esac
    done
fi
exec "$REAL_GIT" "\$@"
WRAPPER
chmod +x /usr/local/bin/git
