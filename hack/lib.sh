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

image_tags() {
  local image="$1" version aliases alias tag out
  version="$(image_meta "$image" version)"
  [[ -n "$version" ]] || die "images/$image/image.yaml has no version"
  [[ -z "$(image_meta "$image" tags)" ]] \
    || die "images/$image/image.yaml: replace tags with aliases; the version tag is derived from version"
  aliases="$(image_meta "$image" aliases)"
  out="$version"
  for alias in $aliases; do
    case "$alias" in
      major)
        [[ "$version" == *.* ]] || die "images/$image/image.yaml: alias major needs a dotted version (got $version)"
        tag="${version%%.*}"
        ;;
      minor)
        [[ "$version" == *.*.* ]] || die "images/$image/image.yaml: alias minor needs a major.minor.patch version (got $version)"
        tag="$(printf '%s\n' "$version" | cut -d. -f1-2)"
        ;;
      [0-9]*)
        die "images/$image/image.yaml: alias $alias pins a version by hand; use major or minor"
        ;;
      *)
        [[ "$alias" =~ ^[A-Za-z_][A-Za-z0-9_.-]*$ ]] || die "images/$image/image.yaml: alias $alias is not a valid tag"
        tag="$alias"
        ;;
    esac
    [[ " $out " == *" $tag "* ]] || out="$out $tag"
  done
  printf '%s\n' "$out"
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
