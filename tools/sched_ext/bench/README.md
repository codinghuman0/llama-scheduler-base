# Step 10 four-phase campaign

The protocol is [BENCHMARK_PROTOCOL.md](../BENCHMARK_PROTOCOL.md). The scripts use Python 3's standard library, GNU 13.3, CMake 3.28.3 and Make 4.3; no packages or services are installed. Run as `codinghuman` (UID 1000), with AC power connected, from this repository. Do not prefix the phase scripts with sudo.

```sh
./tools/sched_ext/bench/step10_phase_a_prepare.sh
./tools/sched_ext/bench/step10_phase_b_arm.sh
# Close Firefox, Codex and unnecessary GUI apps; keep one terminal or TTY.
./tools/sched_ext/bench/step10_phase_c_campaign.sh
# Reopen Firefox/Codex only after CAMPAIGN_COMPLETE.
./tools/sched_ext/bench/step10_phase_d_finalize.sh
```

Each script supports `--help` and `--dry-run`. Dry-run prints a plan and performs no builds, state writes, privilege operations, server execution or network request. Preparation validation uses syntax checks and synthetic data only. The preparation commit does not execute these phases.

Phase A creates `benchmark-results/step10/<UTC-run-id>/` and `.active-run`. It builds A/B/C sequentially in owned temporary detached worktrees, with identical common options. It saves configure/build logs, caches, compile commands, build-info, ELF notes, versions, system dependency identities and file hashes. It extracts the required project-library closure with each server. An explicit bundle-local `LD_LIBRARY_PATH` overrides the build's absolute RUNPATH; dependency resolution and `--version` must pass before the temporary tree is removed. The model is referenced, never copied. D uses exactly C's bytes. A build failure preserves its temporary tree and diagnostics; it does not delete development trees or silently substitute binaries. At least 512 MiB must remain free. The future build's peak size is not known; insufficient capacity stops preparation with evidence.

Phase B revalidates the artifacts, CPU topology, host ABI/boot, free port 8096, disabled sched_ext and absence of project runtime processes. It prints and executes one exact sudo command to start a campaign-specific helper on CPU 10. Enter the password only in your terminal's sudo prompt. The helper does not load sched_ext until a D visit requests it. A/B/C servers and D's launcher/server always run as UID 1000. Do not leave an armed campaign unattended for more than its six-hour helper deadline.

The helper's authenticated SOCK_SEQPACKET interface has a fixed command set: HELLO, CHECK, START for a predefined D visit, STOP, FINISH and ABORT. Commands contain no executable paths, environment, signal numbers or shell text. The helper uses fixed verified scheduler paths and hashes, derives C's server/marker paths from its one prepared campaign, and checks peer UID 1000. The client verifies root peer PID/starttime. It waits on IPC, signals and loader pidfd through blocking selectors, with six-hour total and 20-minute loader safety deadlines. Source/bundle hashes are rechecked; do not change these files while armed. This local helper assumes the authorized UID-1000 repository owner remains trusted; it is not a service for untrusted users.

Phase C pins runner/client to CPU 11. All server TIDs use CPUs `0,2,4,6,8`, five compute/batch threads and two HTTP threads. The root helper/loader use CPU 10. The unchanged D launcher briefly starts with the server mask so its child inherits it, then moves to CPU 11 after registration and before warm-ups. SMT remains enabled, and odd server siblings are unused by the benchmark. The runner refuses Firefox/Codex, compiler/download/stress processes and unsuitable load/temperature/power state. Each of 40 balanced visits starts a fresh server, issues two excluded warm-ups and one measured request, then cleans up. Detailed checks occur outside the timed POST. While timing, the client blocks for the full HTTP response and the root helper waits for events. No phase observer, continuous scan or performance profiler runs.

Every request/response and cleanup result is saved. A failed visit is INVALID, its entire block is unsuitable, and the campaign stops without replacement samples. Root loader cleanup uses exact recorded identities; teardown inventories are saved before assertions and allow the established two-second natural teardown interval. A/B/C normal shutdown uses exact pidfd signaling; an emergency SIGKILL makes the visit fail. No broad kill or BPF deletion exists. If cleanup itself fails, retain the diagnostic directory and inspect the exact recorded process identities before any human recovery; do not rerun the campaign to conceal it.

After all cleanup passes, Phase C asks the helper to exit, verifies it is gone, saves `CAMPAIGN_COMPLETE` and tells you applications may reopen. Phase D validates all 120 saved responses, 40 sample identities/order, affinity/policy checkpoints, model/runtime rehash evidence and cleanup. It then writes the descriptive statistics, 10,000 paired-block bootstrap, fixed decision gates and report. No request is issued by Phase D. Raw data is never discarded and summaries do not modify scheduling policy.

The entire ignored campaign directory is the audit package. Discover it through `benchmark-results/step10/.active-run`. It contains the protocol, request, revisions, runtime bundles, machine snapshots, order, raw visits, `raw-runs.csv`, `summary.csv`, `summary.json`, `protocol-validation.json` and `final-report.md`. A later inspection can interpret it without manually pasted values. Failed/completed directories are never overwritten. Phase A may create a new campaign only after the prior campaign is FAILED or FINALIZED; source/artifact changes and partial campaigns require review rather than automatic resume.

Non-benchmark validation:

```sh
python3 -B tools/sched_ext/bench/test_campaign.py
./tools/sched_ext/bench/step10_phase_a_prepare.sh --dry-run
./tools/sched_ext/bench/step10_phase_b_arm.sh --dry-run
./tools/sched_ext/bench/step10_phase_c_campaign.sh --dry-run
./tools/sched_ext/bench/step10_phase_d_finalize.sh --dry-run
```

These checks use temporary synthetic fixtures and a harmless owned `sleep` process for signal/reap validation. They do not start llama-server, load BPF or send HTTP requests.
