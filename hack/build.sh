#!/usr/bin/env bash
# Build one image with `datumctl compute build` and write it as an OCI archive.
#
#   hack/build.sh <image>
#
# Requires: datumctl with the compute plugin (or the datumctl-compute binary)
# and a BuildKit the plugin can reach: BUILDKIT_HOST, a local buildkitd, or
# Docker's built-in BuildKit. The version is passed to the Dockerfile as
# UPSTREAM_VERSION so image.yaml is the single place a version is pinned.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

image="${1:-}"
[[ -n "$image" ]] || die "usage: $0 <image>"

version="$(image_meta "$image" version)"
tar="$(image_tar "$image")"
dir="$REPO_ROOT/images/$image"

mkdir -p "$DIST_DIR"
rm -f "$tar"

# The Dockerfile's final stage becomes the root filesystem and its CMD the
# instance command. The plugin ships no kernel: the cell boots every image with
# its own platform kernel.
log "building $image $version -> $tar"
compute_build --build-arg "UPSTREAM_VERSION=$version" -o "$tar" "$dir"

log "built $tar ($(du -h "$tar" | cut -f1))"
