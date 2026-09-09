# Security

This document states what a user of `nav_utils` can expect from it in terms of
security, and argues why those expectations hold. Reporting a vulnerability is
described in [SECURITY.md](../SECURITY.md).

## Security requirements

1. **No input can crash the library or the node.** Every value that arrives
   from outside - a velocity command, a voltage, a distance, a path - is
   validated; out-of-range and non-finite values are clamped or rejected, never
   propagated.
2. **The node fails closed.** An unrecognised safety zone scales the velocity
   to zero; a non-finite geometry yields no command rather than a wrong one.
3. **What you run is what was reviewed.** A release artifact can be verified
   back to the commit and the workflow that built it.
4. **No secrets, no cryptography, no network of its own.** The software stores
   no credentials and implements no cryptographic mechanism; all communication
   goes through the ROS 2 middleware the deployment configures.

What the software does **not** promise: authentication or authorisation of
who publishes on its topics, confidentiality of the messages, or protection
against a hostile process on the same host. Those are properties of the ROS 2
deployment (DDS security, host isolation), not of this package.

## Threat model and trust boundaries

```text
   untrusted ──────────────┐            trusted
                           │
  cmd_vel_raw publisher ───┼──> velocity_limiter_node ──> cmd_vel subscriber
  (any DDS participant)    │    [VelocityLimiter]
                           │
  parameters at start ─────┼──> node parameters
  (launch file / CLI)      │
                           │
  library callers ─────────┼──> VelocityLimiter, BatteryMonitor,
  (other packages)         │    SafetyZone, PurePursuit
```

- **Trust boundary 1 - the topic.** Any participant on the DDS domain can
  publish `cmd_vel_raw`. The node treats every message as hostile input:
  limits are applied unconditionally, non-finite components are handled by the
  library, and the elapsed-time computation cannot throw.
- **Trust boundary 2 - the library API.** Callers are other packages in the
  same process. They are trusted not to be malicious but not to be careful:
  every public method validates its arguments (NaN, infinity, negative
  thresholds, empty paths).
- **Trust boundary 3 - the supply chain.** Everything that goes into a build -
  base image, apt packages, GitHub Actions, pip tools - is pinned by hash or
  digest, and the release artifacts are signed with provenance.

Assets: the integrity of the velocity command reaching the drive (a wrong
`cmd_vel` moves a robot), and the integrity of the delivered artifacts.
Out of scope: denial of service by flooding the topic (a DDS concern), and
physical access to the host.

## Assurance case

**Claim:** the security requirements above are met.

### Secure design principles are applied

- *Least privilege* - the node holds no credentials and opens nothing but its
  two topics. In CI every workflow starts with `permissions: {}` and each job
  grants only what it uses; the Scorecard `Token-Permissions` check scores it.
- *Fail-safe defaults* - `SafetyZone::speed_scale` returns 0 for anything
  outside the enumeration; `PurePursuit` returns `std::nullopt` rather than a
  fabricated command; `BatteryMonitor` reads a non-finite voltage as empty.
- *Economy of mechanism* - four value types, one node, no threads, no dynamic
  polymorphism, no exceptions of its own. The whole package is small enough to
  be read in one sitting, which is what makes the rest of this argument
  checkable.
- *Complete mediation* - every public entry point validates its inputs; the
  tests exercise the invalid cases (`test_pure_pursuit`: non-finite geometry,
  NaN points in the path; `test_battery_monitor`: non-finite voltage, unknown
  state; `test_safety_zone`: unknown zone).
- *Open design* - everything, including this document and the CI that
  enforces it, is public.

### Common implementation weaknesses are countered

| Weakness class | Countermeasure | Evidence |
| --- | --- | --- |
| Memory safety (CWE-119/125/787) | No raw pointers or manual allocation; `std::vector`, `std::optional`, `std::ranges`. Hardening flags on every build. Sanitizers, Valgrind and fuzzing on every pull request | `CMakeLists.txt` hardening block; `Runtime analysis` and `Fuzzing` workflows |
| Integer / float misuse (CWE-190/682) | `-Wconversion -Wshadow` as errors; non-finite handling tested; time arithmetic on `int64_t` nanoseconds | `compilers` job with `WARNINGS_AS_ERRORS=ON` |
| Improper input validation (CWE-20) | Validation at every public entry point, tests for each rejected class of input | `src/nav_utils/test/` |
| Uncontrolled exceptions | Nothing in the library throws; the one call in the node that could (`rclcpp::Time` subtraction) was replaced by integer arithmetic | `velocity_limiter_node.cpp` |
| Vulnerable dependencies (CWE-1395) | Dependabot daily, OSV-Scanner and Trivy on every pull request, SBOM per release | `Security` workflow, release assets |
| Supply-chain tampering | Actions, base images and pip tools pinned by hash; keyless cosign signatures and SLSA provenance on every release; zizmor audits the workflows | Scorecard `Pinned-Dependencies`, `Signed-Releases` |
| Leaked credentials (CWE-798) | gitleaks pre-commit and in CI; secret scanning with push protection; checkouts without persisted credentials | `Lint` and `Security` workflows |

### Hardening

Every build enables `-fstack-protector-strong`, `-fstack-clash-protection`,
`-fcf-protection=full`, `_GLIBCXX_ASSERTIONS`, `_FORTIFY_SOURCE=3` (on
optimised builds), full RELRO, `-z now` and a non-executable stack
(`HARDENING=ON` in `CMakeLists.txt`, the default). Each flag is probed before
use so an unsupported compiler builds without it rather than failing.

### Analysis that backs the argument

- Static: clang-tidy (warnings as errors), cppcheck, cpplint, CodeQL
  `security-and-quality`, Semgrep, SonarCloud - on every pull request.
- Dynamic: ASan+UBSan, TSan, Valgrind memcheck on every pull request;
  ClusterFuzzLite with libFuzzer on the controllers, on pull requests and
  nightly.
- Coverage: 100 % of lines and functions, branch coverage measured with
  exception edges excluded ([why](../scripts/strip_exception_branches.py)).

Residual risk: the argument covers the package, not the ROS 2 middleware or
the operating system under it. A defect in `rclcpp` or the DDS vendor is
outside what this project can test; it is inside what Dependabot and
OSV-Scanner watch.

## Verifying a release

Every release ships a source tarball, a Debian package, an SPDX SBOM and
checksums, each with a Sigstore signature bundle, plus SLSA build provenance.
There is no key to obtain: the signatures are keyless, bound to the identity
of the release workflow in this repository.

```bash
TAG=nav_utils-v1.0.0
gh release download "$TAG" --repo wansiedler/perfect_ros2_atomic_package --dir assets
cd assets
sha256sum -c ./*.sha256sums
for bundle in *.sigstore.json; do
  cosign verify-blob --bundle "$bundle" "${bundle%.sigstore.json}" \
    --certificate-identity-regexp '^https://github.com/wansiedler/perfect_ros2_atomic_package/' \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com
done
gh attestation verify ./*.tar.gz --repo wansiedler/perfect_ros2_atomic_package
```

The `verify the release` job runs exactly these commands after every release;
its Summary is the record.
