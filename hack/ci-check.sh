#!/usr/bin/env bash
# Offline checks for every image: scripts parse, metadata is consistent, the
# Dockerfile exists. Building an image needs BuildKit, so the per-image
# workflows do that on the paths they own.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

log "bash syntax"
for f in "$REPO_ROOT"/hack/*.sh; do
  bash -n "$f"
done

log "verify.py compiles"
python3 -c '
import sys
with open(sys.argv[1]) as fh:
    compile(fh.read(), sys.argv[1], "exec")
' "$REPO_ROOT/hack/verify.py"

count=0
for image in $(list_images); do
  log "image $image"
  version="$(image_meta "$image" version)"
  tags="$(image_meta "$image" tags)"
  loader="$(image_meta "$image" loader)"
  [[ -n "$version" ]] || die "images/$image/image.yaml has no version"
  [[ "$loader" == static || "$loader" == dynamic ]] || die "images/$image/image.yaml loader must be static or dynamic (got '$loader')"
  [[ " $tags " == *" $version "* ]] || die "images/$image/image.yaml tags must include the upstream version $version (got: $tags)"
  [[ -f "$REPO_ROOT/images/$image/Dockerfile" ]] || die "images/$image has no Dockerfile"
  count=$((count + 1))
done

[[ "$count" -gt 0 ]] || die "found zero images under images/"
