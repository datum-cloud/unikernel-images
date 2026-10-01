# Building unikernel images

Datum runs each container of a Workload as a [Unikraft](https://unikraft.org)
unikernel. That runtime does not boot ordinary container images, so each
directory under `images/` is a known-good recipe that satisfies the
constraints below. This document explains those constraints, what the
verifier checks, and how to build locally.

## What the runtime accepts

- The image is packaged by `datumctl compute build`: an OCI index whose
  manifest carries `platform.os: kraftcloud` and
  `platform.architecture: x86_64`. A plain `docker build` image has neither
  and does not boot.
- The image ships **only the initrd**: one layer holding the root filesystem
  as an erofs image, plus the OCI config's command, environment, and working
  directory. The cell boots every image with its own platform kernel, which
  is the only kernel wired to the cell's start data (the instance's network
  configuration). An image that carries a kernel of its own boots that kernel
  instead, never learns its VPC address, and sits unreachable while the
  application logs that it is listening. The plugin never embeds one, and the
  verifier rejects an image that has one.
- The root filesystem is extracted into RAM at boot. Images above roughly
  150 MiB fail with an instant platform assertion, so ship a single binary or
  bundle, prune tests, docs, and locales, and never copy a whole `/lib`.
- The entrypoint is a position-independent ELF (`ET_DYN`). Its exact shape
  depends on the `loader` the image declares in `image.yaml`:
  - `static` images ship a **static PIE**: no `PT_INTERP`, no `DT_NEEDED`. Go
    gets there with `-linkmode external -extldflags -static-pie` through a
    cross gcc; Rust with the `x86_64-unknown-linux-musl` target; C with
    `-static-pie`. Plain `CGO_ENABLED=0` Go is `ET_EXEC` and is rejected at
    boot; `-buildmode=pie` alone leaves a `PT_INTERP` and is rejected too.
  - `dynamic` images run ordinary distro binaries through a dynamic loader
    shipped in the image. The root filesystem must then contain the loader
    and the exact transitive shared-library closure. Compute it with `ldd` at
    build time, as the `nginx`, `redis`, and `python` Dockerfiles do, rather
    than hand-listing libraries; keep libraries in the loader's compiled-in
    search directories (`/lib/x86_64-linux-gnu`, `/usr/lib/x86_64-linux-gnu`);
    and do not ship `/etc/ld.so.cache`, which names libraries that are not
    there.
- One process runs as root. There are no `/dev/stdout` symlinks, no
  fork-based supervision, and no persistent disk: turn off daemonising and
  worker forking, point logs at stderr, and disable persistence.

## Networking

Datum compute networks are IPv6-first: an instance's interface gets an IPv6
address, and an IPv4-only listener is unreachable. Every network-serving image
therefore listens on the unspecified address of both families (`::` and
`0.0.0.0`, or a dual-stack `::` socket), and its `image.yaml` records this as
`listen: dual-stack`. Keep the same shape when you override the command or
ship your own server: bind `[::]:<port>` (or the empty host, which most
runtimes treat as dual-stack), never `0.0.0.0` or `127.0.0.1` alone. Where a
server refuses IPv4-mapped clients on an IPv6 socket, bind both addresses
(nginx keeps `ipv6only=on`, so its config has two `listen` lines; memcached
sets `IPV6_V6ONLY`, so its command omits `-l` and takes the default of binding
both).

## Base userlands: busybox, debian, ubuntu

`busybox`, `debian`, and `ubuntu` are minimal userlands with a shell as the
entrypoint. They are directly runnable, intended for instance shell sessions,
debugging, and one-off commands: override the container command in the
Workload (for example `["/bin/sh", "-c", "sleep infinity"]` to keep an
instance up, or a script mounted from a ConfigMap).

They are not `FROM` bases. A packaged image contains an initrd, not container
layers, so Docker cannot build on top of it. To build your own image "on
Debian", start your Dockerfile from the upstream `debian:13-slim` image and
package it with `datumctl compute build` exactly as `images/debian/` does.

## Building locally

Prerequisites: `datumctl` with the compute plugin (or the `datumctl-compute`
binary on `PATH`), Docker (the plugin uses its built-in BuildKit; set
`BUILDKIT_HOST` to use another daemon), `erofs-utils` for verification, and
`crane` for pushing.

```sh
hack/build.sh nginx          # datumctl compute build -> dist/nginx-<version>.tar
hack/verify.sh nginx         # checks the artifact
REGISTRY=localhost:5555/unikernel hack/push.sh nginx   # optional: push to a local registry
```

`hack/build.sh` runs `datumctl compute build` on `images/<image>/`, passing
`version` from `image.yaml` to the Dockerfile as `UPSTREAM_VERSION`, and
writes the OCI archive to `dist/`. The Dockerfile's final stage is the root
filesystem and its `CMD` is the instance command. The Dockerfiles build the
root filesystem for `linux/amd64`; on an arm64 host the `RUN` steps need
binfmt emulation (Docker Desktop and colima provide it), while the Go and
Rust images cross-compile from a native stage.

`hack/verify.sh` rejects an artifact that will not boot on a cell: it checks
the index platform, that no kernel layer is present, the initrd size ceiling,
that the entrypoint named by the OCI config exists and is `ET_DYN`, and that
the ELF shape matches the declared loader (no interpreter or shared libraries
for `static`; interpreter and full shared-library closure resolvable inside
the root filesystem for `dynamic`).

## Publishing (CI)

Each image has a workflow under `.github/workflows/<image>.yaml` that calls
the shared `build-image.yaml`. On a pull request it builds and verifies the
image and uploads the OCI archive as a workflow artifact. On a push to `main`,
on the weekly schedule, and on manual dispatch it also pushes the image to
`ghcr.io/datum-cloud/unikernel/<image>` under every tag listed in
`image.yaml`, using `GITHUB_TOKEN` with `packages: write`. No other
credentials are needed.

Repository setup that is not automated:

- **Package visibility**: GHCR creates packages as private on first push.
  For each `unikernel/<image>` package, set visibility to **Public** once and
  link it to this repository.
- **Dependency updates**: Renovate bumps `version:` in `image.yaml` from
  Docker Hub tags (patch and minor only) through `renovate.json`, and keeps
  the workflows' actions current.

Recipes for many more applications exist upstream in
[unikraft-cloud/examples](https://github.com/unikraft-cloud/examples) and
[unikraft/catalog](https://github.com/unikraft/catalog); adapt their
Dockerfiles rather than starting from scratch.
