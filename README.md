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

- **Small.** Each image ships only the application and the files it needs,
  from under 2 MiB for busybox to a few tens of megabytes for full runtimes.
- **Fast.** Instances boot in well under a second.
- **Dual-stack.** Every network image listens on IPv6 and IPv4 out of the box.
  Datum compute networks are IPv6-first, so this is what makes the image
  reachable the moment it starts.
- **Tracks upstream.** Tags follow the upstream version and are rebuilt weekly,
  so patch releases flow through without any change on your side.

## Using an image

```yaml
apiVersion: compute.datumapis.com/v1alpha
kind: Workload
metadata:
  name: web
spec:
  template:
    spec:
      runtime:
        resources:
          instanceType: datumcloud/d1-standard-2
        sandbox:
          containers:
            - name: nginx
              image: ghcr.io/datum-cloud/unikernel/nginx:1.30
              ports:
                - name: http
                  port: 8080
                  protocol: TCP
      networkInterfaces:
        - network:
            name: default
  placements:
    - name: default
      cityCodes: [DFW]
      scaleSettings:
        minReplicas: 1
```

Set the container `command`/`args` to run something other than the default
(for example your own script in the `python` image, mounted from a
ConfigMap). Instances keep no state across restarts: the root filesystem lives
in RAM. Tags are rebuilt in place; deploy by digest when you need a
reproducible rollout.

## Images

Images are added one directory at a time under `images/`; each directory's
`image.yaml` records the upstream version, the published tags, the default
port, and the runtime it builds against. Browse the directory for the current
catalogue.

## Requesting or contributing an image

Open an issue to request one, or send a pull request that adds
`images/<name>/` together with its workflow. Each image is its own build
pipeline: a change to that directory builds and verifies the image on the
pull request, and publishes it when the change lands on `main`.
[CONTRIBUTING.md](CONTRIBUTING.md) walks through the layout, and
[docs/building.md](docs/building.md) explains the constraints a unikernel
image has to meet (position-independent entrypoints, shipping the exact
shared-library closure, the root filesystem size ceiling, and why the images
carry no kernel).

## License

Apache-2.0; see [LICENSE](LICENSE).
