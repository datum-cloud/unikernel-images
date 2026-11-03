# UPSTREAM_VERSION is the BusyBox release; the Alpine release that ships it is
# pinned here and must be bumped together with image.yaml.
ARG UPSTREAM_VERSION
FROM --platform=linux/amd64 alpine:3.22 AS build

ARG UPSTREAM_VERSION
RUN <<'EOS'
set -eu
busybox | head -1 | grep -q "BusyBox v${UPSTREAM_VERSION}" || { echo "alpine ships $(busybox | head -1), expected ${UPSTREAM_VERSION}"; exit 1; }
mkdir -p /rootfs/bin /rootfs/lib /rootfs/etc /rootfs/tmp /rootfs/root
cp /bin/busybox /rootfs/bin/busybox
# ld-musl is both the dynamic loader and libc; libc.musl-* is its soname alias.
cp /lib/ld-musl-x86_64.so.1 /rootfs/lib/ld-musl-x86_64.so.1
ln -s ld-musl-x86_64.so.1 /rootfs/lib/libc.musl-x86_64.so.1
# Applet symlinks so PATH lookups (sh, ls, wget, httpd, ...) resolve.
cd /rootfs
for applet in $(busybox --list); do ln -sf /bin/busybox "bin/$applet"; done
cp /etc/passwd /etc/group /rootfs/etc/
EOS

FROM scratch
COPY --from=build /rootfs /

CMD ["/bin/sh"]
