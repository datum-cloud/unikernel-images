# Unikernel images for Datum Cloud

Ready-to-run unikernel images for [Datum Cloud](https://datum.net) compute.
Reference one in a Workload the same way you would reference a container image
and it boots as a unikernel on a Datum cell:

```
ghcr.io/datum-cloud/unikernel/<name>:<version>
```

`<name>` is the upstream project name (`nginx`, `redis`, `python`, ...) and
`<version>` is the upstream software version, never a distro release or a
date. Every image also publishes its minor line (`1.30`), its major line where
that is meaningful (`8`), and `latest`.

## What you get

- **Small.** Each image ships only the application and the files it needs:
  single-binary images are a few megabytes, full runtimes under 130 MB.
- **Fast.** Instances boot in well under a second.
- **Dual-stack.** Every network image listens on IPv6 and IPv4 out of the box.
  Datum compute networks are IPv6-first, so this is what makes the image
  reachable the moment it starts.
- **Tracks upstream.** Tags follow the upstream version and are rebuilt weekly,
  so patch releases flow through without any change on your side.

## Using an image

Deploy one with `datumctl`. The image name is the only thing that changes
from deploying any other container; `--runtime-class=unikernel` puts the
Instances on the unikernel tier.

```sh
datumctl compute deploy web \
  --image=ghcr.io/datum-cloud/unikernel/nginx:1.30 \
  --city=DFW --http-port=8080 --runtime-class=unikernel
```

A successful deploy prints the HTTPS URL the workload is published on. Omit
`--http-port` for internal services such as `redis` or `memcached`; they are
reachable on their port from other Instances on the same network.

Shell images open at a prompt, so they work as scratch machines:

```sh
datumctl compute deploy scratch \
  --image=ghcr.io/datum-cloud/unikernel/debian:13 \
  --city=DFW --runtime-class=unikernel
datumctl compute exec scratch-dfw-0 -it -- bash
```

Everything else is ordinary workload management: `datumctl compute scale`,
`restart`, `instances`, and `destroy` all apply. Use `-f` with a manifest when
you need more than the flags express, for example a custom `command` or a
ConfigMap mounted into the `python` image.

Instances keep no state across restarts: the root filesystem lives in RAM.
Tags are rebuilt in place; deploy by digest when you need a reproducible
rollout.

## Images

Images are added one directory at a time under `images/`; each directory's
`image.yaml` records the upstream version, the published tags, the default
port, and whether the entrypoint is a static PIE or ships its own dynamic
loader. Browse the directory for the current catalogue.

## Requesting or contributing an image

Open an issue to request one, or send a pull request that adds
`images/<name>/` together with its workflow. Each image is an ordinary
Dockerfile packaged with `datumctl compute build`, and each is its own build
pipeline: a change to that directory builds and verifies the image on the
pull request, and publishes it when the change lands on `main`.
[CONTRIBUTING.md](CONTRIBUTING.md) walks through the layout, and
[docs/building.md](docs/building.md) explains the constraints a unikernel
image has to meet (position-independent entrypoints, shipping the exact
shared-library closure, the root filesystem size ceiling, and why the images
carry no kernel).

## License

Apache-2.0; see [LICENSE](LICENSE).
