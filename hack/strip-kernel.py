#!/usr/bin/env python3
"""Rewrite an exported kraft OCI layout tarball so it ships only the initrd.

    hack/strip-kernel.py <layout.tar>

kraft packages the runtime kernel it built against (official/base or
base-compat) into the image next to the rootfs. Datum cells do not boot that
kernel: the cell's runtime hands its own platform kernel to any image packaged
without one, and that kernel is the only one wired to the cell's start data
(network configuration, environment). An image that carries its own kernel
boots it instead, never learns its VPC address, and is unreachable even
though the application starts and the instance reports Available.

The rewrite keeps the initrd layer and the OCI config's Cmd/Env/WorkingDir,
drops the kernel and kernel.dbg layers, and reduces the index entry to
platform {os: kraftcloud, architecture: x86_64}, the shape that
`datumctl compute build` produces and that the runtime accepts.
Standard library only, in place.
"""

import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile

INITRD_ANNOTATION = "org.unikraft.kernel.initrd"
KEPT_CONFIG_KEYS = ("Cmd", "Entrypoint", "Env", "WorkingDir")


def write_blob(blobs, obj):
    data = json.dumps(obj, separators=(",", ":")).encode()
    digest = hashlib.sha256(data).hexdigest()
    with open(os.path.join(blobs, digest), "wb") as f:
        f.write(data)
    return "sha256:" + digest, len(data)


def strip(layout):
    blobs = os.path.join(layout, "blobs", "sha256")

    def read(digest):
        with open(os.path.join(blobs, digest.split(":", 1)[1])) as f:
            return json.load(f)

    with open(os.path.join(layout, "index.json")) as f:
        index = json.load(f)
    entries = [m for m in index["manifests"] if m.get("platform", {}).get("os") == "kraftcloud"]
    if len(entries) != 1:
        sys.exit("expected exactly one kraftcloud manifest in the index, found %d" % len(entries))
    manifest = read(entries[0]["digest"])
    config = read(manifest["config"]["digest"])

    layers = manifest["layers"]
    diff_ids = config["rootfs"]["diff_ids"]
    if len(layers) != len(diff_ids):
        sys.exit("layer/diff_id count mismatch")
    kept = [(l, d) for l, d in zip(layers, diff_ids) if INITRD_ANNOTATION in l.get("annotations", {})]
    if len(kept) != 1:
        sys.exit("expected exactly one layer annotated %s" % INITRD_ANNOTATION)
    initrd, initrd_diff = kept[0]

    new_config = {
        "architecture": "x86_64",
        "os": "kraftcloud",
        "created": config.get("created", "0001-01-01T00:00:00Z"),
        "history": [{"created": "0001-01-01T00:00:00Z"}],
        "rootfs": {"type": "layers", "diff_ids": [initrd_diff]},
        "config": {k: v for k, v in config.get("config", {}).items() if k in KEPT_CONFIG_KEYS},
    }
    if not (new_config["config"].get("Cmd") or new_config["config"].get("Entrypoint")):
        sys.exit("OCI config has no Cmd/Entrypoint")
    config_digest, config_size = write_blob(blobs, new_config)

    new_manifest = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "size": config_size,
            "digest": config_digest,
        },
        "layers": [{
            "mediaType": initrd["mediaType"],
            "size": initrd["size"],
            "digest": initrd["digest"],
            "annotations": {INITRD_ANNOTATION: initrd["annotations"][INITRD_ANNOTATION]},
        }],
    }
    manifest_digest, manifest_size = write_blob(blobs, new_manifest)

    new_index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": [{
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "size": manifest_size,
            "digest": manifest_digest,
            "platform": {"architecture": "x86_64", "os": "kraftcloud"},
            "artifactType": "application/vnd.oci.image.config.v1+json",
        }],
    }
    with open(os.path.join(layout, "index.json"), "w") as f:
        json.dump(new_index, f, separators=(",", ":"))

    keep = {manifest_digest, config_digest, initrd["digest"]}
    for name in os.listdir(blobs):
        if "sha256:" + name not in keep:
            os.remove(os.path.join(blobs, name))
    return initrd["size"]


def main(tar_path):
    tmp = tempfile.mkdtemp()
    try:
        with tarfile.open(tar_path) as t:
            t.extractall(tmp)
        size = strip(tmp)
        with tarfile.open(tar_path + ".tmp", "w") as t:
            for name in sorted(os.listdir(tmp)):
                t.add(os.path.join(tmp, name), arcname=name)
        os.replace(tar_path + ".tmp", tar_path)
        print("stripped kernel layers; initrd layer %.1f MiB" % (size / 2**20))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: strip-kernel.py <layout.tar>")
    main(sys.argv[1])
