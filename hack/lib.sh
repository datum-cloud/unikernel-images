#!/usr/bin/env bash
# Shared helpers for the hack/ scripts. Source, do not execute.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGISTRY="${REGISTRY:-ghcr.io/datum-cloud/unikernel}"
DIST_DIR="${DIST_DIR:-$REPO_ROOT/dist}"
BUILDKIT_CONTAINER="${BUILDKIT_CONTAINER:-buildkit}"
BUILDKIT_HOST="${BUILDKIT_HOST:-docker-container://$BUILDKIT_CONTAINER}"

# Runtime images are resolved by fully-qualified name so that kraft never has
# to guess a registry. base/base-compat are the enterprise elfloader kernels
# that Datum cells boot; pulling them needs index.unikraft.io credentials.
RUNTIME_BASE="${RUNTIME_BASE:-index.unikraft.io/official/base:latest}"
RUNTIME_BASE_COMPAT="${RUNTIME_BASE_COMPAT:-index.unikraft.io/official/base-compat:latest}"

# kraft would otherwise phone home on every invocation.
export KRAFTKIT_NO_CHECK_UPDATES=true

log() { printf '==> %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

# image_meta <image> <key>: read a scalar from images/<image>/image.yaml.
# image.yaml is deliberately flat (key: value per line) so no YAML parser is
# needed on either macOS or the CI runner.
image_meta() {
  local file="$REPO_ROOT/images/$1/image.yaml"
  [[ -f "$file" ]] || die "no such image: $1 ($file missing)"
  sed -n "s/^$2:[[:space:]]*//p" "$file" | sed 's/[[:space:]]*#.*$//; s/^"//; s/"$//'
}

image_ref() { echo "$REGISTRY/$1:$(image_meta "$1" version)"; }
image_tar() { echo "$DIST_DIR/$1-$(image_meta "$1" version).tar"; }

list_images() { ls "$REPO_ROOT/images"; }
