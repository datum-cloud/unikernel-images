# Contributing

Every image is one directory under `images/` and one workflow under
`.github/workflows/`. Nothing else in the repository needs to change to add
an image.

## Adding an image

1. Create `images/<name>/` containing:
   - `image.yaml`: flat `key: value` metadata. `version` is the upstream
     software version and the single place it is pinned; `tags` lists every
     tag to publish (the version, its minor and major lines, `latest`);
     `runtime` is `base` or `base-compat`; `port` and `listen: dual-stack`
     describe the default command.
   - `Dockerfile`: multi-stage; the final stage is `FROM scratch` and ships
     only what runs. Declare `ARG UPSTREAM_VERSION` and use it in `FROM`.
   - `Kraftfile`: `spec: v0.6`, the runtime, `targets: [kraftcloud/x86_64]`,
     `rootfs: ./Dockerfile`, and `cmd`.
   - Any sample app or config the default command needs.
2. Create `.github/workflows/<name>.yaml` by copying an existing image
   workflow and changing the image name. It calls the shared
   `build-image.yaml` workflow, which builds and verifies on pull requests
   and publishes on `main`, weekly, and on demand.
3. Build and verify locally (`hack/build.sh <name> && hack/verify.sh <name>`),
   boot it on a Datum cell, and confirm it answers over IPv6 before opening
   the pull request.

[docs/building.md](docs/building.md) covers what the verifier checks and why.

## Updating an image

Bump `version` (and `tags`) in `image.yaml`. Renovate proposes these bumps for
images whose `upstream` is a Docker Hub repository. Versions always track
upstream: do not introduce tags of your own.

## Conventions

- Keep the root filesystem small: it is extracted into RAM and images above
  about 150 MiB do not boot.
- Bind listeners dual-stack (`[::]` plus `0.0.0.0`, or a dual-stack socket);
  Datum compute networks are IPv6-first.
- One process, no daemonising, logs to stderr, no persistent disk.
