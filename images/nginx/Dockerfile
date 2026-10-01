ARG UPSTREAM_VERSION
FROM --platform=linux/amd64 nginx:${UPSTREAM_VERSION}-trixie AS build

# Assemble the rootfs under /rootfs: the binary plus the exact shared-library
# closure it loads, computed with ldd at build time. Copying a whole /lib is
# not an option because the rootfs is extracted into RAM on boot.
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
copy_closure /usr/sbin/nginx
mv /rootfs/usr/sbin/nginx /rootfs/usr/bin/nginx 2>/dev/null || { mkdir -p /rootfs/usr/bin; mv /rootfs/usr/sbin/nginx /rootfs/usr/bin/nginx; }
# nginx opens its compiled-in log paths before reading the config; the stock
# image symlinks them to /dev/stdout, which the unikernel does not provide.
# It also writes its pid to the compiled-in /run/nginx.pid even with
# master_process off, and exits with "open() /run/nginx.pid failed" when the
# directory is missing (the stock image gets /run from the base layer).
mkdir -p /rootfs/var/log/nginx /rootfs/var/cache/nginx /rootfs/run /rootfs/var/run /rootfs/etc/nginx
: > /rootfs/var/log/nginx/access.log
: > /rootfs/var/log/nginx/error.log
cp -r /etc/nginx/mime.types /etc/nginx/fastcgi_params /etc/nginx/scgi_params /etc/nginx/uwsgi_params /rootfs/etc/nginx/
cp /etc/passwd /etc/group /rootfs/etc/
EOS

FROM scratch
COPY --from=build /rootfs /
COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /wwwroot/index.html
