ARG UPSTREAM_VERSION
FROM --platform=linux/amd64 memcached:${UPSTREAM_VERSION}-trixie AS build
# The upstream image drops to the memcache user; the rootfs assembly needs root.
USER root

RUN <<'EOS'
set -eu
copy_closure() {
  for f in "$@"; do
    mkdir -p "/rootfs$(dirname "$f")"; cp -L "$f" "/rootfs$f"
    ldd "$f" | awk '$2=="=>"{print $3} $1 ~ /^\//{print $1}' | sort -u | while read -r lib; do
      [ -e "$lib" ] || continue
      mkdir -p "/rootfs$(dirname "$lib")"; cp -L "$lib" "/rootfs$lib"
    done
  done
}
copy_closure /usr/local/bin/memcached
mkdir -p /rootfs/usr/bin /rootfs/etc
mv /rootfs/usr/local/bin/memcached /rootfs/usr/bin/memcached
cp /etc/passwd /etc/group /rootfs/etc/
EOS

FROM scratch
COPY --from=build /rootfs /
