#!/usr/bin/env bash
# Verify that an exported OCI layout tarball is a bootable Datum unikernel image.
#
#   hack/verify.sh <image>            # verifies dist/<image>-<version>.tar
#   hack/verify.sh path/to/image.tar [base|base-compat]
#
# Checks:
#   * the OCI index has a manifest with platform os=kraftcloud/arch=x86_64
#     (anything else will not boot on a cell)
#   * no kernel layer is embedded: the cell boots its own platform kernel, and
#     an image that carries one boots it instead and never gets its network
#   * the initrd layer unpacks and the OCI config Cmd names an ELF in it
#   * the entrypoint ELF shape matches the runtime:
#       base        -> ET_DYN, no PT_INTERP, no DT_NEEDED (static PIE)
#       base-compat -> ET_DYN, PT_INTERP present in the rootfs, and every
#                      DT_NEEDED resolvable inside the rootfs (transitively)
#   * the initrd stays under the ~150 MiB RAM-extraction ceiling

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

target="${1:-}"
[[ -n "$target" ]] || die "usage: $0 <image>|<layout.tar> [base|base-compat]"

if [[ -f "$target" ]]; then
  tar="$target"
  runtime_kind="${2:-}"
else
  tar="$(image_tar "$target")"
  runtime_kind="${2:-$(image_meta "$target" runtime)}"
fi
[[ -f "$tar" ]] || die "no such file: $tar (run hack/build.sh first)"
[[ -n "$runtime_kind" ]] || die "runtime kind required (base|base-compat)"

exec python3 "$REPO_ROOT/hack/verify.py" "$tar" "$runtime_kind"
