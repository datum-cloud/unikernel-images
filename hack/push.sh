#!/usr/bin/env bash
# Push a built image to the registry under every tag listed in image.yaml.
#
#   hack/push.sh <image>
#
# Pushes the built OCI archive (index + kraftcloud manifest) with crane so the
# platform metadata the build wrote survives untouched, then adds the
# remaining tags server-side. Authenticate first with `crane auth login`.
# Point REGISTRY at a local registry (e.g. localhost:5555/unikernel) to inspect
# an image without publishing it.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

image="${1:-}"
[[ -n "$image" ]] || die "usage: $0 <image>"

version="$(image_meta "$image" version)"
tags="$(image_meta "$image" tags)"
tar="$(image_tar "$image")"
repo="$REGISTRY/$image"
[[ -f "$tar" ]] || die "no such file: $tar (run hack/build.sh first)"

layout="$(mktemp -d)"
trap 'rm -rf "$layout"' EXIT
tar -xf "$tar" -C "$layout"

log "pushing $repo:$version"
crane push --index "$layout" "$repo:$version"
for tag in $tags; do
  [[ "$tag" == "$version" ]] && continue
  log "tagging $repo:$tag"
  crane tag "$repo:$version" "$tag"
done
