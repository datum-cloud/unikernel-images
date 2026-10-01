#!/usr/bin/env python3
"""Verify a `datumctl compute build` OCI archive (see verify.sh for the checks).

Standard library plus fsck.erofs, so it runs unchanged on macOS and
ubuntu-latest without binutils: ELF parsing is done by hand.
"""

import io
import json
import os
import struct
import subprocess
import sys
import tarfile
import tempfile

# Empirical ceiling for the initrd that the runtime extracts into RAM; images
# above it fail with an instant platform assertion.
INITRD_LIMIT = 150 * 1024 * 1024

# Directories the glibc loader searches without ld.so.cache, plus those the
# platform puts in LD_LIBRARY_PATH. Images must not rely on ld.so.cache.
DEFAULT_LIB_DIRS = [
    "/lib/x86_64-linux-gnu", "/usr/lib/x86_64-linux-gnu",
    "/lib64", "/usr/lib64", "/usr/local/lib", "/usr/lib", "/lib",
]

PT_INTERP, PT_DYNAMIC = 3, 2
DT_NULL, DT_NEEDED, DT_STRTAB, DT_STRSZ, DT_RPATH, DT_RUNPATH = 0, 1, 5, 10, 15, 29
ET_EXEC, ET_DYN = 2, 3

failures = []


def fail(msg):
    failures.append(msg)
    print(f"FAIL {msg}")


def ok(msg):
    print(f"ok   {msg}")


class Elf:
    def __init__(self, data):
        if data[:4] != b"\x7fELF":
            raise ValueError("not an ELF file")
        if data[4] != 2:
            raise ValueError("not a 64-bit ELF")
        self.data = data
        (self.type, self.machine) = struct.unpack_from("<HH", data, 16)
        (self.phoff,) = struct.unpack_from("<Q", data, 32)
        (self.phentsize, self.phnum) = struct.unpack_from("<HH", data, 54)
        self.phdrs = []
        for i in range(self.phnum):
            off = self.phoff + i * self.phentsize
            p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = \
                struct.unpack_from("<IIQQQQQQ", data, off)
            self.phdrs.append((p_type, p_offset, p_vaddr, p_filesz))

    def interp(self):
        for p_type, off, _, size in self.phdrs:
            if p_type == PT_INTERP:
                return self.data[off:off + size].rstrip(b"\0").decode()
        return None

    def _vaddr_to_off(self, vaddr):
        # Map a virtual address to a file offset via the PT_LOAD that covers it.
        for p_type, off, va, size in self.phdrs:
            if p_type == 1 and va <= vaddr < va + size:
                return off + (vaddr - va)
        raise ValueError("vaddr %#x not in any PT_LOAD" % vaddr)

    def dynamic(self):
        """Return (needed[], runpath[]) from the PT_DYNAMIC segment."""
        for p_type, off, _, size in self.phdrs:
            if p_type == PT_DYNAMIC:
                break
        else:
            return [], []
        entries = []
        for i in range(size // 16):
            tag, val = struct.unpack_from("<qQ", self.data, off + i * 16)
            if tag == DT_NULL:
                break
            entries.append((tag, val))
        strtab = next((v for t, v in entries if t == DT_STRTAB), None)
        if strtab is None:
            return [], []
        stroff = self._vaddr_to_off(strtab)

        def cstr(idx):
            end = self.data.index(b"\0", stroff + idx)
            return self.data[stroff + idx:end].decode()

        needed = [cstr(v) for t, v in entries if t == DT_NEEDED]
        runpath = []
        for t, v in entries:
            if t in (DT_RPATH, DT_RUNPATH):
                runpath.extend(p for p in cstr(v).split(":") if p)
        return needed, runpath


def extract_erofs(path, dest):
    """Unpack the erofs root filesystem at path into dest with fsck.erofs."""
    subprocess.run(
        ["fsck.erofs", "-d0", "--no-preserve", "--extract=" + dest, path],
        check=True,
    )


def rootfs_path(root, path):
    """Resolve an absolute in-image path against the extracted rootfs.

    Symlinks are followed inside the rootfs: absolute targets are re-rooted
    rather than escaping to the host (busybox applets are `sh -> /bin/busybox`,
    merged-usr distros have `/lib -> usr/lib`).
    """
    cur = root
    parts = [p for p in path.split("/") if p and p != "."]
    hops = 0
    while parts:
        part = parts.pop(0)
        if part == "..":
            cur = root if cur == root else os.path.dirname(cur)
            continue
        nxt = os.path.join(cur, part)
        if os.path.islink(nxt):
            hops += 1
            if hops > 40:
                raise ValueError("symlink loop resolving %s" % path)
            target = os.readlink(nxt)
            if target.startswith("/"):
                cur = root
                parts = [p for p in target.split("/") if p and p != "."] + parts
            else:
                parts = [p for p in target.split("/") if p and p != "."] + parts
            continue
        cur = nxt
    return cur


def find_lib(root, name, runpath):
    for d in runpath + DEFAULT_LIB_DIRS:
        p = rootfs_path(root, os.path.join(d, name))
        if os.path.exists(p):
            return p
    return None


def check_closure(root, elf_path, elf, interp):
    """Walk DT_NEEDED transitively; report every soname that cannot resolve."""
    # musl's loader is also its libc: requests for libc.musl-*.so.1 or libc.so
    # are satisfied by the ld-musl loader itself.
    musl = interp and "ld-musl" in interp
    seen, missing, queue = set(), [], [(elf_path, elf)]
    while queue:
        path, e = queue.pop()
        needed, runpath = e.dynamic()
        runpath = [p.replace("$ORIGIN", os.path.dirname(path)) for p in runpath]
        for name in needed:
            if name in seen:
                continue
            seen.add(name)
            if musl and (name.startswith("libc.musl-") or name == "libc.so"):
                continue
            found = find_lib(root, name, runpath)
            if not found:
                missing.append(name)
                continue
            with open(found, "rb") as f:
                queue.append(("/" + os.path.relpath(found, root), Elf(f.read())))
    return sorted(seen), missing


def main(tar_path, loader):
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(tar_path) as t:
            t.extractall(tmp)
        with open(os.path.join(tmp, "index.json")) as f:
            index = json.load(f)

        # --- index / platform -------------------------------------------------
        candidates = [
            m for m in index.get("manifests", [])
            if m.get("platform", {}).get("os") == "kraftcloud"
            and m.get("platform", {}).get("architecture") == "x86_64"
        ]
        if not candidates:
            fail("no manifest with platform os=kraftcloud, architecture=x86_64 in index")
            return
        ok("index has a kraftcloud/x86_64 manifest")
        m = candidates[0]

        def blob(digest):
            return os.path.join(tmp, "blobs", *digest.split(":"))

        with open(blob(m["digest"])) as f:
            manifest = json.load(f)
        with open(blob(manifest["config"]["digest"])) as f:
            config = json.load(f)

        kernel = initrd = None
        for layer in manifest["layers"]:
            ann = layer.get("annotations", {})
            if "org.unikraft.kernel.image" in ann:
                kernel = layer
            if "org.unikraft.kernel.initrd" in ann:
                initrd = layer
        # The cell boots its own platform kernel; an embedded one is booted
        # instead and never receives the cell's start data (no network).
        if kernel:
            fail("kernel layer present (%.1f MiB)" % (kernel["size"] / 2**20))
        else:
            ok("no embedded kernel layer (the cell supplies its platform kernel)")
        if not initrd:
            fail("no layer annotated org.unikraft.kernel.initrd")
            return

        # --- initrd / rootfs --------------------------------------------------
        layer_dir = os.path.join(tmp, "layer")
        with tarfile.open(blob(initrd["digest"])) as t:
            t.extractall(layer_dir)
        initrd_file = os.path.join(layer_dir, initrd["annotations"]["org.unikraft.kernel.initrd"].lstrip("/"))
        initrd_size = os.path.getsize(initrd_file)
        if initrd_size <= INITRD_LIMIT:
            ok("initrd %.1f MiB (limit %d MiB)" % (initrd_size / 2**20, INITRD_LIMIT / 2**20))
        else:
            fail("initrd %.1f MiB exceeds the %d MiB boot ceiling" % (initrd_size / 2**20, INITRD_LIMIT / 2**20))
        root = os.path.join(tmp, "rootfs")
        extract_erofs(initrd_file, root)

        cmd = config.get("config", {}).get("Cmd") or config.get("config", {}).get("Entrypoint")
        if not cmd:
            fail("OCI config has no Cmd")
            return
        entry = cmd[0]
        entry_path = rootfs_path(root, entry)
        if os.path.isfile(entry_path):
            ok("entrypoint %s present in rootfs (cmd: %s)" % (entry, " ".join(cmd)))
        else:
            fail("entrypoint %s not found in rootfs" % entry)
            return

        # --- ELF shape ---------------------------------------------------------
        with open(entry_path, "rb") as f:
            elf = Elf(f.read())
        if elf.machine != 62:
            fail("entrypoint is not x86_64 (e_machine=%d)" % elf.machine)
        if elf.type == ET_DYN:
            ok("entrypoint is ET_DYN (position-independent)")
        else:
            fail("entrypoint is e_type=%d; the elfloader only accepts ET_DYN (PIE)" % elf.type)
        interp = elf.interp()
        needed, runpath = elf.dynamic()

        if loader == "static":
            if interp is None:
                ok("no PT_INTERP (static)")
            else:
                fail("PT_INTERP %s present; declared static, build a static PIE or declare loader: dynamic" % interp)
            if not needed:
                ok("no DT_NEEDED entries")
            else:
                fail("DT_NEEDED present on a static image: %s" % needed)
        elif loader == "dynamic":
            if interp is None:
                # A static PIE needs no loader; nothing further to check.
                ok("no PT_INTERP (static PIE)")
            else:
                if os.path.exists(rootfs_path(root, interp)):
                    ok("PT_INTERP %s present in rootfs" % interp)
                else:
                    fail("PT_INTERP %s missing from rootfs" % interp)
                seen, missing = check_closure(root, entry, elf, interp)
                if missing:
                    fail("unresolved shared libraries: %s" % missing)
                else:
                    ok("shared-library closure resolves (%d sonames)" % len(seen))
            if os.path.exists(rootfs_path(root, "/etc/ld.so.cache")):
                print("warn /etc/ld.so.cache shipped; it may reference libraries that are not in the image")
        else:
            fail("unknown loader %r (expected static|dynamic)" % loader)

    if failures:
        print("\n%d check(s) failed" % len(failures))
        sys.exit(1)
    print("\nall checks passed")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: verify.py <image.tar> <static|dynamic>")
    main(sys.argv[1], sys.argv[2])
