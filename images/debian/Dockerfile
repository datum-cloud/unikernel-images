ARG UPSTREAM_VERSION
FROM --platform=linux/amd64 debian:${UPSTREAM_VERSION}-slim AS build

# Trim everything that is dead weight in a RAM-resident rootfs: package
# manager caches, docs, locales. The dpkg database is kept so the image stays
# recognisably Debian (dpkg -l works) and small enough to boot.
RUN <<'EOS'
set -eu
rm -rf /var/lib/apt/lists/* /var/cache/apt/* /var/cache/debconf/*-old \
       /usr/share/doc/* /usr/share/man/* /usr/share/info/* /usr/share/locale/* \
       /var/log/* /var/lib/dpkg/*-old /usr/share/lintian /tmp/* /var/tmp/*
mkdir -p /tmp /var/tmp /run
chmod 1777 /tmp /var/tmp
EOS

FROM scratch
COPY --from=build / /

CMD ["/bin/bash"]
