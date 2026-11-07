ARG UPSTREAM_VERSION
FROM --platform=linux/amd64 python:${UPSTREAM_VERSION}-trixie AS build

# Ship the interpreter, libpython, and the shared-library closure of every
# stdlib extension module (ldd over lib-dynload/*.so pulls in libssl, liblzma,
# libbz2, ...). A hand-written list misses some; computing it keeps the image
# correct across upstream bumps.
RUN <<'EOS'
set -eu
PYVER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
copy_closure() {
  for f in "$@"; do
    ldd "$f" 2>/dev/null | awk '$2=="=>"{print $3} $1 ~ /^\//{print $1}' | sort -u | while read -r lib; do
      [ -e "$lib" ] || continue
      case "$lib" in
        /lib/x86_64-linux-gnu/*|/usr/lib/x86_64-linux-gnu/*|/lib64/*|/lib/*.so*|/usr/lib/*.so*) dest="/rootfs$lib" ;;
        # Not in a compiled-in loader search dir (e.g. /usr/local/lib), and we
        # do not ship ld.so.cache; relocate so the loader finds it.
        *) dest="/rootfs/usr/lib/x86_64-linux-gnu/$(basename "$lib")" ;;
      esac
      mkdir -p "$(dirname "$dest")"; cp -L "$lib" "$dest"
    done
  done
}
mkdir -p /rootfs/usr/bin /rootfs/usr/local/lib /rootfs/tmp
cp -L "/usr/local/bin/python${PYVER}" /rootfs/usr/bin/python3
copy_closure "/usr/local/bin/python${PYVER}" /usr/local/lib/python${PYVER}/lib-dynload/*.so
# Standard library, minus what is never useful in a server unikernel.
cp -r "/usr/local/lib/python${PYVER}" "/rootfs/usr/local/lib/python${PYVER}"
cd "/rootfs/usr/local/lib/python${PYVER}"
rm -rf test tests idlelib tkinter turtledemo ensurepip site-packages/pip site-packages/setuptools \
       lib2to3 pydoc_data config-*-x86_64-linux-gnu
find . -name '__pycache__' -type d -prune -exec rm -rf {} +
find . -name 'test' -type d -prune -exec rm -rf {} +
EOS

FROM scratch
COPY --from=build /rootfs /
COPY server.py /src/server.py

CMD ["/usr/bin/python3", "/src/server.py"]
