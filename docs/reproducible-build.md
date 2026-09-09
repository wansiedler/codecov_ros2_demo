# Reproducible build

Two clean builds of the same commit in the CI image produce bit-for-bit
identical binaries. `make reproducible` proves it: it builds twice from
scratch in the dev container, hashes `libnav_utils_core.a`, the node and every
test binary, and fails if any hash differs.

```bash
make reproducible
```

What makes it hold:

- **Same inputs** - the CI image is pinned by digest, so the compiler, the
  standard library and every ROS dependency are the same bytes on every run.
- **Same paths** - the workspace is always `/home/dev/ws` in the container
  (`/__w/<repo>/<repo>` in CI), so nothing that embeds a path differs between
  builds.
- **No timestamps** - the code uses no `__DATE__`/`__TIME__`, and CMake does
  not embed one.
- **ccache is off** for the check (`CMAKE_*_COMPILER_LAUNCHER` cleared), so a
  cache hit cannot stand in for a real second build.

Known gap: the Debian package built by `make deb` embeds the build time in its
control data, so two `.deb` files differ while their contents do not. Setting
`SOURCE_DATE_EPOCH` from the tag date closes it; that is on the
[roadmap](../ROADMAP.md).
