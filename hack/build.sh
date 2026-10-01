#!/usr/bin/env bash
# Build one image with kraft and export it as an OCI layout tarball.
#
#   hack/build.sh <image>
#
# Requires: kraft, docker (for the buildkit container). The BuildKit host is
# created on demand; override BUILDKIT_HOST to use an existing one.
# The version is passed to the Dockerfile as UPSTREAM_VERSION so image.yaml is
# the single place a version is pinned.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

image="${1:-}"
[[ -n "$image" ]] || die "usage: $0 <image>"

version="$(image_meta "$image" version)"
runtime_kind="$(image_meta "$image" runtime)"
ref="$(image_ref "$image")"
tar="$(image_tar "$image")"
dir="$REPO_ROOT/images/$image"

case "$runtime_kind" in
  base) runtime="$RUNTIME_BASE" ;;
  base-compat) runtime="$RUNTIME_BASE_COMPAT" ;;
  *) die "image.yaml runtime must be 'base' or 'base-compat' (got '$runtime_kind')" ;;
esac

# Start a BuildKit daemon if the default docker-container host is requested
# and nothing is listening yet.
if [[ "$BUILDKIT_HOST" == "docker-container://$BUILDKIT_CONTAINER" ]] \
   && ! docker inspect -f '{{.State.Running}}' "$BUILDKIT_CONTAINER" 2>/dev/null | grep -q true; then
  log "starting buildkit container '$BUILDKIT_CONTAINER'"
  docker rm -f "$BUILDKIT_CONTAINER" >/dev/null 2>&1 || true
  docker run -d --name "$BUILDKIT_CONTAINER" --privileged moby/buildkit:latest >/dev/null
  sleep 2
fi

mkdir -p "$DIST_DIR"
rm -f "$tar"

log "packaging $ref (runtime $runtime)"
# The rootfs is packaged as CPIO: an erofs initrd does not boot on base-compat
# (instant platform assertion, no console output). The Kraftfile pins the
# runtime kind; --runtime here resolves it to the fully-qualified image.
kraft pkg \
  --workdir "$dir" \
  --name "$ref" \
  --runtime "$runtime" \
  --plat kraftcloud --arch x86_64 \
  --rootfs-type cpio \
  --build-arg "UPSTREAM_VERSION=$version" \
  --buildkit-host "$BUILDKIT_HOST" \
  --no-prompt --log-type basic \
  "$dir"

log "exporting $ref -> $tar"
kraft pkg export --log-type basic -o "$tar" "$ref" >/dev/null

# The cell boots its own platform kernel; an embedded one is booted instead
# and cannot take the cell's start data, leaving the instance unreachable.
log "dropping the embedded runtime kernel from $tar"
python3 "$REPO_ROOT/hack/strip-kernel.py" "$tar"

log "built $tar ($(du -h "$tar" | cut -f1))"
