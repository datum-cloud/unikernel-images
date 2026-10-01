ARG UPSTREAM_VERSION
# Build natively and cross-compile for the musl x86_64 target, whose
# self-contained CRT objects let the cross gcc produce a static PIE without a
# musl sysroot on the host.
FROM --platform=$BUILDPLATFORM rust:${UPSTREAM_VERSION}-trixie AS build
RUN apt-get update && apt-get install -y --no-install-recommends gcc-x86-64-linux-gnu \
    && rm -rf /var/lib/apt/lists/* \
    && rustup target add x86_64-unknown-linux-musl
WORKDIR /src
COPY main.rs ./
RUN rustc -O --target x86_64-unknown-linux-musl \
      -C linker=x86_64-linux-gnu-gcc -C link-self-contained=yes \
      -C relocation-model=pic -o /server main.rs

FROM scratch
COPY --from=build /server /server
