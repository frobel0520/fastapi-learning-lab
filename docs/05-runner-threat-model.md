# 05 Runner Threat Model

## Scope

The runner accepts untrusted Python submitted by an anonymous learner. The protected assets are the FastAPI host process, host filesystem, container engine, other executions, network credentials, service availability, and grading integrity.

## Trust boundaries

```text
browser (untrusted code)
  → FastAPI validation and queue boundary
    → Runner protocol
      → ephemeral container (hostile workload)
        → structured ExecutionResult
```

The FastAPI process never imports or evaluates learner code. The local adapter sends a bounded JSON payload over stdin. No host directory, socket, token, environment secret, or container-engine socket is mounted into the workload.

## Threats and controls

| Threat | Local control | Automated evidence |
|---|---|---|
| Infinite loop / CPU exhaustion | 6 s host timeout (15 s for the CPU-heavy password-hashing and multi-request OAuth2 scopes checks), 0.5 CPU, two concurrent slots | `test_infinite_loop_times_out` and per-lesson matrix |
| Output flood | streamed stdout/stderr, 64 KB hard limit | `test_output_flood_is_terminated` |
| Memory exhaustion | 192 MB container limit | command contract test; destructive stress test deferred |
| Fork / process bomb | 64 PID limit | command contract test; destructive stress test deferred |
| External network access | `--network none` | `test_container_security_boundary` |
| Host filesystem mutation | read-only rootfs, isolated 32 MB tmpfs, no mounts | `test_container_security_boundary` |
| Database exercise leakage | SQL lessons use a per-execution in-memory SQLite database with no host mount | per-lesson SQL CRUD matrix + container cleanup |
| Privilege escalation | UID 65532, all capabilities dropped, no-new-privileges | command contract + security probe |
| File descriptor / large file abuse | nofile 64, fsize 1 MB | command contract test |
| Image drift / surprise pulls | pinned dependencies, `--pull never` at execution | image build + command contract test |
| Queue exhaustion | two slots, one-second acquisition timeout | unit contract; load test deferred |
| Stale workloads | unique names, `--rm`, forced cleanup on timeout/error | `test_no_runner_containers_are_left_behind` |
| Checker mismatch | every reference solution runs against its checker | `test_all_reference_solutions_pass` |

## Accepted limitations for local v1

- A developer who controls the local image can inspect checker implementation; checks are correctness feedback, not secret certification exams.
- Container isolation depends on the Podman/Docker daemon, Linux kernel, and default seccomp profile being patched and correctly configured.
- Memory bombs and fork bombs are not actively launched in shared CI; their flags are contract-tested. A dedicated disposable security environment is required for destructive probes.
- The local queue is process-local and does not provide distributed fairness, identity quotas, or abuse accounting.

## Browser runner (GitHub Pages)

The static site has no server. Learner code runs in the learner's own browser tab, inside a dedicated Web Worker running Pyodide. The protected assets shrink to the learner's tab responsiveness and the integrity of feedback.

| Threat | Browser control | Automated evidence |
|---|---|---|
| Infinite loop / CPU exhaustion | 20 s timeout, then the worker is terminated and rebuilt on the next run; the UI thread stays responsive | manual browser check; CI cannot interrupt a busy in-process runtime |
| Output flood | stdout/stderr writes fail beyond 64 KB; unbuffered streams keep rejected output out of the next run | `verify:browser-runner` flood + reuse checks |
| Checker mismatch between runtimes | the same `harness.py` runs in Pyodide against every reference solution | `browser-runner` CI job |
| State leaking between lessons | SQLModel metadata cleared before every run; each run re-executes `main.py` in a fresh namespace | per-lesson matrix in one runtime |
| Dependency drift | Pyodide version and package pins are constants; a unit test keeps pins equal to the runner image | `pyodide-core.test.ts` |

Accepted limitations:

- Hidden checks and reference solutions are shipped to the browser. Checks are learning feedback, not certification.
- Worker code can use the network and the site's origin like any script the learner pastes into DevTools. Only run code you understand; the site stores nothing beyond local workspace drafts.
- Pyodide and packages load from jsDelivr and PyPI at pinned top-level versions; transitive dependencies follow the Pyodide lock and PyPI resolution.
- Requires WebAssembly JSPI (verified on Chrome). Browsers without it get an `unavailable` result instead of a partial run.

## Cloudflare handoff requirements

`CloudflareSandboxRunner` must preserve the request and response schema, one execution per isolated sandbox lifecycle, network policy, timeout, output bounds, non-root execution, concurrency controls, cleanup evidence, and the same solution matrix. Platform-specific limits must be recorded before the public release gate is approved.
