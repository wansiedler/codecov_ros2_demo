# Roadmap

The project is a reference: one small, real ROS 2 package with every quality
gate a production package should have, kept green. The roadmap follows from
that - the pipeline is the product, the package is the specimen.

## In scope for the next year

- **Keep every gate current.** Dependabot moves the pins; a green CI on the
  newest toolchain, ROS 2 patch release and scanner version is the baseline,
  not a feature.
- **ROS 2 distribution tracking.** Build and test against the next LTS
  distribution when it ships (the `C++26 canary` job is the same idea for the
  language). The single-package layout makes the switch one tag change.
- **Reproducible Debian package.** The binaries are bit-for-bit reproducible
  ([docs/reproducible-build.md](docs/reproducible-build.md)); the `.deb`
  still embeds a build timestamp. Set `SOURCE_DATE_EPOCH` from the tag and
  verify the package the same way.
- **Coverage of the launch test.** The node is exercised over real topics but
  its lines are not in the C++ coverage figure. Collect the node process's
  gcov data from the launch test.
- **A second maintainer.** The one item on this list that is not a pull
  request; see [GOVERNANCE.md](GOVERNANCE.md#continuity).

## Out of scope

- **Growing the package.** No new controllers, no navigation stack. Four
  classes and one node are enough to exercise every gate; more code would only
  dilute the point.
- **Robot-specific integration.** Hardware drivers, simulation worlds, launch
  files for a particular platform - none of it belongs here.
- **Supporting old ROS 2 distributions.** The package tracks the current LTS
  and the next one; it is not a compatibility layer.

This file is revised at each major release and whenever the answer to "what is
the pipeline missing?" changes.
