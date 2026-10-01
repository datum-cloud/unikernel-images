#!/usr/bin/env bash
# Verify that a built OCI archive is a bootable Datum unikernel image.
#
#   hack/verify.sh <image>            # verifies dist/<image>-<version>.tar
#   hack/verify.sh path/to/image.tar [static|dynamic]
#
# Checks:
#   * the OCI index has a manifest with platform os=kraftcloud/arch=x86_64
#     (anything else will not boot on a cell)
#   * no kernel layer is embedded: the cell boots its own platform kernel, and
#     an image that carries one boots it instead and never gets its network
#   * the initrd (an erofs root filesystem) unpacks and the OCI config Cmd
#     names an ELF in it
#   * the entrypoint ELF shape matches the loader declared in image.yaml:
#       static  -> ET_DYN, no PT_INTERP, no DT_NEEDED (static PIE)
#       dynamic -> ET_DYN, PT_INTERP present in the rootfs, and every
#                  DT_NEEDED resolvable inside the rootfs (transitively)
#   * the initrd stays under the ~150 MiB RAM-extraction ceiling
#
# Requires fsck.erofs (erofs-utils) to unpack the root filesystem.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

target="${1:-}"
[[ -n "$target" ]] || die "usage: $0 <image>|<image.tar> [static|dynamic]"

if [[ -f "$target" ]]; then
  tar="$target"
  loader="${2:-}"
else
  tar="$(image_tar "$target")"
  loader="${2:-$(image_meta "$target" loader)}"
fi
[[ -f "$tar" ]] || die "no such file: $tar (run hack/build.sh first)"
[[ -n "$loader" ]] || die "loader required (static|dynamic)"
command -v fsck.erofs >/dev/null || die "fsck.erofs not found (install erofs-utils)"

exec python3 "$REPO_ROOT/hack/verify.py" "$tar" "$loader"
