ARG UPSTREAM_VERSION
# Build on the host's native architecture and cross-link for x86_64 so the Go
# toolchain never runs under emulation. The elfloader on base only accepts a
# static PIE: -buildmode=pie alone leaves a PT_INTERP, so link externally with
# -static-pie against the x86_64 cross toolchain.
FROM --platform=$BUILDPLATFORM golang:1.27-trixie AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc-x86-64-linux-gnu libc6-dev-amd64-cross \
    && rm -rf /var/lib/apt/lists/*
ARG UPSTREAM_VERSION
# `go install pkg@version` refuses GOBIN when cross-compiling and drops the
# binary under $GOPATH/bin/<GOOS>_<GOARCH>/ (plain $GOPATH/bin on an amd64
# host), so locate it afterwards instead of naming the path.
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=1 CC=x86_64-linux-gnu-gcc GOOS=linux GOARCH=amd64 \
    go install -buildmode=pie -trimpath -tags netgo \
      -ldflags='-s -w -linkmode external -extldflags "-static-pie"' \
      github.com/caddyserver/caddy/v2/cmd/caddy@v${UPSTREAM_VERSION} \
    && mkdir -p /out && cp "$(find /go/bin -type f -name caddy | head -1)" /out/caddy
RUN echo "127.0.0.1 localhost" > /tmp/hosts

FROM scratch
COPY --from=build /out/caddy /usr/bin/caddy
COPY --from=build /tmp/hosts /etc/hosts
COPY Caddyfile /etc/caddy/Caddyfile
COPY index.html /var/www/index.html

CMD ["/usr/bin/caddy", "run", "--config", "/etc/caddy/Caddyfile"]
