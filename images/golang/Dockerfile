ARG UPSTREAM_VERSION
# Build on the host's native architecture and cross-link for x86_64 so the Go
# toolchain never runs under emulation.
#
# The elfloader only accepts a position-independent executable, and a scratch
# rootfs has no dynamic loader, so the binary must be a STATIC PIE. Pure-Go
# -buildmode=pie still records a PT_INTERP pointing at ld-linux; linking
# externally with -static-pie against the x86_64 cross toolchain removes the
# interpreter and every shared-library dependency.
FROM --platform=$BUILDPLATFORM golang:${UPSTREAM_VERSION}-trixie AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc-x86-64-linux-gnu libc6-dev-amd64-cross \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY go.mod main.go ./
RUN --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=1 CC=x86_64-linux-gnu-gcc GOOS=linux GOARCH=amd64 \
    go build -buildmode=pie -trimpath \
      -ldflags='-s -w -linkmode external -extldflags "-static-pie"' -o /server .

FROM scratch
COPY --from=build /server /server
