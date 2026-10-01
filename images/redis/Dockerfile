ARG UPSTREAM_VERSION
FROM --platform=linux/amd64 redis:${UPSTREAM_VERSION}-trixie AS build

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
copy_closure /usr/local/bin/redis-server
mkdir -p /rootfs/usr/bin /rootfs/data /rootfs/etc/redis
mv /rootfs/usr/local/bin/redis-server /rootfs/usr/bin/redis-server
EOS

FROM scratch
COPY --from=build /rootfs /
COPY redis.conf /etc/redis/redis.conf

CMD ["/usr/bin/redis-server", "/etc/redis/redis.conf"]
