ARG UPSTREAM_VERSION
FROM --platform=linux/amd64 node:${UPSTREAM_VERSION}-alpine AS build

# The Alpine build of node is a dynamic musl binary: ship it with the musl
# loader/libc and the C++ runtime it links, and nothing else.
RUN <<'EOS'
set -eu
mkdir -p /rootfs/usr/bin /rootfs/lib /rootfs/usr/lib /rootfs/etc /rootfs/tmp
cp /usr/local/bin/node /rootfs/usr/bin/node
ldd /usr/local/bin/node | awk '$2=="=>"{print $3} $1 ~ /^\//{print $1}' | sort -u | while read -r lib; do
  [ -e "$lib" ] || continue
  mkdir -p "/rootfs$(dirname "$lib")"; cp -L "$lib" "/rootfs$lib"
done
ln -sf ld-musl-x86_64.so.1 /rootfs/lib/libc.musl-x86_64.so.1
cp /etc/os-release /rootfs/etc/os-release
EOS

FROM scratch
COPY --from=build /rootfs /
COPY server.js /usr/src/server.js
