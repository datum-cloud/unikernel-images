# Building unikernel images

Datum runs each container of a Workload as a [Unikraft](https://unikraft.org)
unikernel. That runtime does not boot ordinary container images, so each
directory under `images/` is a known-good recipe that satisfies the
constraints below. This document explains those constraints, what the
verifier checks, and how to build locally.

## What the runtime accepts

- The image is packaged by `kraft`: an OCI index whose manifest carries
  `platform.os: kraftcloud` and `platform.architecture: x86_64`. A plain
  `docker build` image has neither and does not boot.
- The image ships **only the initrd**: one layer holding the root filesystem
  as a CPIO archive, plus the OCI config's command, environment, and working
  directory. The cell boots every image with its own platform kernel, which
  is the only kernel wired to the cell's start data (the instance's network
  configuration). `kraft pkg` embeds the runtime kernel it built against; an
  image that carries it boots that kernel instead, never learns its VPC
  address, and sits unreachable while the application logs that it is
  listening. `hack/strip-kernel.py` removes that layer after every build.
- The root filesystem is extracted into RAM at boot. Images above roughly
  150 MiB fail with an instant platform assertion, so ship a single binary or
  bundle, prune tests, docs, and locales, and never copy a whole `/lib`.
- The entrypoint is a position-independent ELF (`ET_DYN`). Its exact shape
  depends on the runtime the image declares in `image.yaml`:
  - `base` runs **static PIEs**: no `PT_INTERP`, no `DT_NEEDED`. Go gets
    there with `-linkmode external -extldflags -static-pie` through a cross
    gcc; Rust with the `x86_64-unknown-linux-musl` target; C with
    `-static-pie`. Plain `CGO_ENABLED=0` Go is `ET_EXEC` and is rejected at
    boot; `-buildmode=pie` alone leaves a `PT_INTERP` and is rejected too.
  - `base-compat` adds a dynamic loader for ordinary distro binaries. The
    root filesystem must then contain the loader and the exact transitive
    shared-library closure. Compute it with `ldd` at build time, as the
    `nginx`, `redis`, and `python` Dockerfiles do, rather than hand-listing
    libraries; keep libraries in the loader's compiled-in search directories
    (`/lib/x86_64-linux-gnu`, `/usr/lib/x86_64-linux-gnu`); and do not ship
    `/etc/ld.so.cache`, which names libraries that are not there.
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

The IPv6 socket is opened by the cell's platform kernel, not by the kernel the
image was built against, so the `CONFIG_LWIP_IPV6` setting of the locally
cached runtime does not matter.

## Base userlands: busybox, debian, ubuntu

`busybox`, `debian`, and `ubuntu` are minimal userlands with a shell as the
entrypoint. They are directly runnable, intended for instance shell sessions,
debugging, and one-off commands: override the container command in the
Workload (for example `["/bin/sh", "-c", "sleep infinity"]` to keep an
instance up, or a script mounted from a ConfigMap).

They are not `FROM` bases. A kraft-packaged image contains an initrd, not
container layers, so Docker cannot build on top of it. To build your own image
"on Debian", start your Dockerfile from the upstream `debian:13-slim` image
and package it with a Kraftfile exactly as `images/debian/` does.

## Building locally

Prerequisites: `kraft` 0.12.x, Docker (a BuildKit container is started on
demand), `crane` for pushing, Python 3 for verification.

```sh
hack/build.sh nginx          # kraft pkg + export + strip -> dist/nginx-<version>.tar
hack/verify.sh nginx         # checks the artifact
REGISTRY=localhost:5555/unikernel hack/push.sh nginx   # optional: push to a local registry
```

`hack/build.sh` packages `images/<image>/` with `kraft pkg` for
`kraftcloud/x86_64`, passing `version` from `image.yaml` to the Dockerfile as
`UPSTREAM_VERSION`, exports the OCI layout tarball to `dist/`, and strips the
embedded kernel. The Dockerfiles build the root filesystem for `linux/amd64`;
on an arm64 host the `RUN` steps need binfmt emulation (Docker Desktop and
colima provide it), while the Go and Rust images cross-compile from a native
stage.

`hack/verify.sh` rejects an artifact that will not boot on a cell: it checks
the index platform, that no kernel layer is present, the initrd size ceiling,
that the entrypoint named by the OCI config exists and is `ET_DYN`, and that
the ELF shape matches the declared runtime (static for `base`; interpreter
and full shared-library closure resolvable inside the root filesystem for
`base-compat`).

### Runtime images and credentials

Every Kraftfile references `index.unikraft.io/official/base:latest` or
`official/base-compat:latest`, the enterprise elfloader kernels. Pulling them
requires an `index.unikraft.io` account allowed to read `official/*`
(`kraft login index.unikraft.io`); a robot account scoped to a namespace such
as `datum/` cannot. Once pulled they live in kraft's local store
(`~/.local/share/kraftkit/runtime/oci`) and later builds reuse them offline.
The kernel is never shipped (see above); the runtime kind still matters at
build time because it decides which loader the root filesystem must contain.

## Publishing (CI)

Each image has a workflow under `.github/workflows/<image>.yaml` that calls
the shared `build-image.yaml`. On a pull request it builds and verifies the
image and uploads the OCI layout as a workflow artifact. On a push to `main`,
on the weekly schedule, and on manual dispatch it also pushes the image to
`ghcr.io/datum-cloud/unikernel/<image>` under every tag listed in
`image.yaml`, using `GITHUB_TOKEN` with `packages: write`.

Repository setup that is not automated:

- **Secrets**: `UNIKRAFT_INDEX_USER` and `UNIKRAFT_INDEX_TOKEN` with read
  access to `index.unikraft.io/official/*`. Builds fail at the login step
  until they exist.
- **Package visibility**: GHCR creates packages as private on first push.
  For each `unikernel/<image>` package, set visibility to **Public** once and
  link it to this repository.
- **Dependency updates**: `renovate.json` bumps `version:` in `image.yaml`
  from Docker Hub tags (patch and minor only) if Renovate is enabled for the
  organisation; `.github/dependabot.yml` covers the workflows' actions.

Recipes for many more applications exist upstream in
[unikraft-cloud/examples](https://github.com/unikraft-cloud/examples) and
[unikraft/catalog](https://github.com/unikraft/catalog); adapt those rather
than starting from scratch.
