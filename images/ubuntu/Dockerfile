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
EOS

FROM scratch
COPY --from=build / /
