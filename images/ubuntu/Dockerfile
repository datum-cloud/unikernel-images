ARG UPSTREAM_VERSION
FROM --platform=linux/amd64 ubuntu:${UPSTREAM_VERSION} AS build

# Same trimming as the debian image; see images/debian/Dockerfile.
RUN <<'EOS'
set -eu
rm -rf /var/lib/apt/lists/* /var/cache/apt/* /var/cache/debconf/*-old \
       /usr/share/doc/* /usr/share/man/* /usr/share/info/* /usr/share/locale/* \
       /var/log/* /var/lib/dpkg/*-old /usr/share/lintian /tmp/* /var/tmp/*
mkdir -p /tmp /var/tmp /run
chmod 1777 /tmp /var/tmp
# The image packer stores every hardlink as a full copy, and Ubuntu's Rust
# coreutils is over a hundred links to one 11 MiB multicall binary, which
# would inflate the root filesystem past the boot ceiling. Point the extra
# names at the first one with relative symlinks; argv[0] still carries the
# applet name, so dispatch is unchanged.
find / -xdev -type f -links +1 -printf '%i %p\n' | sort -n \
  | awk '$1 == prev { print keep, $2; next } { prev = $1; keep = $2 }' \
  | while read -r keep dup; do ln -sfr "$keep" "$dup"; done
EOS

FROM scratch
COPY --from=build / /

CMD ["/bin/bash"]
