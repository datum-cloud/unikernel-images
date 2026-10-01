#!/usr/bin/env bash
# Shared helpers for the hack/ scripts. Source, do not execute.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGISTRY="${REGISTRY:-ghcr.io/datum-cloud/unikernel}"
DIST_DIR="${DIST_DIR:-$REPO_ROOT/dist}"

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

# compute_build <args...>: run `datumctl compute build`. CI installs the plugin
# binary on its own, without datumctl, so prefer it when it is on PATH.
compute_build() {
  if command -v datumctl-compute >/dev/null 2>&1; then
    datumctl-compute build "$@"
  else
    datumctl compute build "$@"
  fi
}
