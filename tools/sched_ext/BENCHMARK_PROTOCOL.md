# Lightweight base measurement protocol

Status: frozen by Step 10.1. This document defines future measurement; Step 10.1 executes no build, inference, benchmark, perf, contention workload, or scheduler activation. No performance result is recorded here. Implementation changes and Step 10.2 execution require separate authorization.

## Purpose and revision identities

Measure whether the lightweight infrastructure is cheap enough to support later optimization. Keep the neutral scheduler unchanged and keep phase out of scheduling decisions.

| Config | Exact source revision | Phase hint | Scheduler | Meaning |
| --- | --- | --- | --- | --- |
| A | `original-performance-baseline-v1`, `7a2db1a0cf38e5f4eb278a58c3903d295258d0ea` | Option absent | Default Linux, raw policy 0 | Original implementation |
| B | `llama-side-lightweight-v1`, `c8b9d61d12b4997d902a03e5dc55a185d18c3bc9` | OFF | Default Linux, raw policy 0 | Frozen fork without hints |
| C | Same llama-side revision as B | ON | Default Linux, raw policy 0 | Frozen fork with hints |
| D | Exactly C's executable and complete shared-library set; scheduler `neutral-sched-ext-base-v1`, `ea4a36bbad1100d7d3f7c6aa57caadcb782a26fa` | ON | Selected server/TIDs raw policy 7 | Neutral sched_ext base |

`one-repo-golden-validation-v1` remains `542850645a54fc2e35a9a8189ff8dfcf35b9c51d`; its instrumentation is excluded. The neutral tag still names its implementation commit even after this documentation commit.

Interpret A -> B as the fork/base implementation delta, B -> C as the phase-hint transport delta, and C -> D as the **neutral sched_ext-base delta**. C -> D is not pure sched_ext framework overhead: D also changes scheduling semantics to the validated Linux v6.17 scx_simple weighted-vtime baseline with partial switching, selected-child control plane and PID-scoped marker attachment. No phase, load, topology or worker policy is enabled.

## Inspected tooling and reuse decisions

Read-only inspection covered `scripts/server-bench.py`, `tools/server/bench/bench.py`, `tools/server/bench/speed-bench/speed_bench.py`, and the archived `results/compute-profile-20260905T044005Z/{REPRODUCE.md,workload.py,commands-performance*.json}` methodology.

Reuse the established loopback `/completion` endpoint, health gate, fixed seed/temperature, `cache_prompt=false`, `ignore_eos=true`, normal response `timings`, command manifests and raw-result preservation. The archive also establishes logical batch 512 and physical ubatch 256. Do not execute the old scripts unchanged: they include random/dataset prompts, streaming/token-interval timing, multiple slots, concurrency, multiple scenarios or a different thread/profile experiment. SPEED-Bench also requires an external dataset. None implements this A/B/C/D lifecycle and order exactly. This document is sufficient to freeze the runner contract; no runner is added in Step 10.1.

The only existing llama build in the active repository is `build-lightweight-dev`: GNU 13.3.0, Unix Makefiles, RelWithDebInfo (`-O2 -g -DNDEBUG`), shared libraries ON, native CPU/OpenMP ON, HINT ON, TRACE OFF. It has the server and marker DSO, but `common/build-info.cpp` reports `LLAMA_COMMIT="e5b385887"`, rather than the frozen llama-side revision, and there is no exact frozen-build manifest establishing that revision. It is **not certified for A/B/C/D reuse**. Do not infer build provenance from the current worktree HEAD. Its validated functionality remains authoritative; its measurement-build provenance is insufficient. No existing A or B build was found in the inspected original/semantic worktrees.

The existing neutral scheduler artifacts are the Step 9 validated artifacts and can be reused only if their hashes and host ABI still match:

| Artifact under `tools/sched_ext/` | SHA-256 |
| --- | --- |
| `build/llama_scx.bpf.o` | `45ae9ae69ee9ab2ecf7ea6a326b33db52d75dd100f16901068a335f95f6cd86c` |
| `build/bin/llama_scx` | `2e6abb63c5a7519cdb01becaf7df0fdf8966a15afcc67f9800849c54843f7341` |
| `build/bin/llama_scx_child` | `459669650fdf02cd9642410d30ec022bb09c0915021f291d014a22714514210a` |

## Model and machine identity

Use only `/home/codinghuman/projects/model.gguf`, readable by UID 1000. Its size is **1117321312 bytes** and SHA-256 is **`f3bdf9cf31dee4b57ae4e455a1cb0d01b5c2c1b50d72d3112141c195506c2840`**. All configurations use this exact file; record its hash before and after the campaign. Do not copy or download a model.

The inspected host has an AMD Ryzen 5 5500U with Radeon Graphics, one socket, six physical cores, twelve logical CPUs, one NUMA node, online CPUs `0-11`. SMT is active (`smt/active=1`, `smt/control=on`). Sysfs gives the following sibling evidence; lscpu's displayed core IDs are normalized differently, so the CPU sibling pairs are the binding identity:

| Server CPU | SMT sibling | Sysfs package/core |
| --- | --- | --- |
| 0 | 1 | 0/0 |
| 2 | 3 | 0/1 |
| 4 | 5 | 0/2 |
| 6 | 7 | 0/4 |
| 8 | 9 | 0/5 |
| 10 | 11 | 0/6 |

The primary server CPU set is exactly **`0,2,4,6,8,10`**, mask `0x555`, one logical CPU per physical core. Use this set for every server and every server-created TID. Verify it through `os.sched_getaffinity(tid)`. Do not choose alternate CPUs, change SMT globally, sweep threads, use CPU shielding, or isolate CPUs through kernel settings. Pin the single request/control client to CPU **1** in every configuration; pin D's root loader to CPU **1** as well. The idle D launcher inherits the server mask. SMT siblings remain available to ordinary system tasks; background sanity and balanced order control their influence.

The inspected kernel is `7.0.0-34-generic`; freeze one kernel/boot environment for a complete campaign. The scheduler's Git freeze is not kernel-specific. Record kernel, boot ID, BTF hash, online/allowed CPUs and topology at campaign start/end. Stop if these change mid-campaign; a different host/kernel requires a separately reviewed protocol amendment, not silent substitution.

## Build protocol (future Step 10.2 only)

Build A, B and C once before measurement. D reuses **the exact C bytes**, including `llama-server`, `libllama-server-impl.so`, `libllama.so`, `libggml*.so` and other resolved runtime libraries; there is no fourth llama build. Use clean source/build trees at the exact revisions. Do not rebuild the validated development tree.

Use `/usr/bin/cc` and `/usr/bin/c++`, resolving to GNU gcc/g++ **13.3.0**, CMake **3.28.3**, and GNU Make **4.3** with generator **Unix Makefiles**. Ninja is not installed and is not a dependency. Freeze Release optimization (`-O3 -DNDEBUG`), shared libraries, native architecture (`GGML_NATIVE=ON`, effective `-march=native` on this host), OpenMP, CPU repacking and llamafile behavior equally. No additional `CFLAGS`/`CXXFLAGS`, LTO, sanitizers, profiling, compiler substitution or ccache-based provenance assumptions are allowed. Record full versions, compiler hashes, configure argv, complete caches and compile commands.

Future source/build locations:

```text
A_SRC=/home/codinghuman/projects/llama.cpp-original-baseline
A_BUILD=/home/codinghuman/projects/llama.cpp-original-baseline/build-step10-a
LW_SRC=/home/codinghuman/projects/llama.cpp-step10-frozen
B_BUILD=/home/codinghuman/projects/llama.cpp-step10-frozen/build-step10-b
C_BUILD=/home/codinghuman/projects/llama.cpp-step10-frozen/build-step10-c
```

The existing A worktree must remain clean at its exact tag. The future `LW_SRC` is one detached worktree at `llama-side-lightweight-v1`, shared by the two distinct B/C build directories. Creating these directories/worktrees is not part of Step 10.1.

The following commands are frozen requirements, **not executed in Step 10.1**:

```bash
common=(
  -G "Unix Makefiles"
  -DCMAKE_C_COMPILER=/usr/bin/cc -DCMAKE_CXX_COMPILER=/usr/bin/c++
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS= -DCMAKE_CXX_FLAGS=
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DBUILD_SHARED_LIBS=ON
  -DGGML_CPU=ON -DGGML_NATIVE=ON -DGGML_OPENMP=ON
  -DGGML_CPU_REPACK=ON -DGGML_LLAMAFILE=ON
  -DGGML_BACKEND_DL=OFF -DGGML_CPU_ALL_VARIANTS=OFF
  -DGGML_BLAS=OFF -DGGML_CUDA=OFF -DGGML_VULKAN=OFF
  -DGGML_METAL=OFF -DGGML_HIP=OFF -DGGML_SYCL=OFF -DGGML_OPENCL=OFF
  -DGGML_RPC=OFF -DGGML_LTO=OFF -DGGML_CCACHE=OFF
  -DLLAMA_BUILD_COMMON=ON -DLLAMA_BUILD_TOOLS=ON -DLLAMA_BUILD_SERVER=ON
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_APP=OFF
  -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF -DLLAMA_BUILD_MTMD=OFF
  -DLLAMA_OPENSSL=OFF -DLLAMA_SUBPROCESS=ON -DLLAMA_USE_SYSTEM_GGML=OFF
)
cmake -S "$A_SRC" -B "$A_BUILD" "${common[@]}"
cmake -S "$LW_SRC" -B "$B_BUILD" "${common[@]}" -DLLAMA_SCX_PHASE_HINT=OFF -DLLAMA_SCX_PHASE_TRACE=OFF
cmake -S "$LW_SRC" -B "$C_BUILD" "${common[@]}" -DLLAMA_SCX_PHASE_HINT=ON -DLLAMA_SCX_PHASE_TRACE=OFF
cmake --build "$A_BUILD" --target llama-server --parallel 6
cmake --build "$B_BUILD" --target llama-server --parallel 6
cmake --build "$C_BUILD" --target llama-server --parallel 6
```

`LLAMA_BUILD_TOOLS=ON` is required by the common tools/server build gate, but build only the `llama-server` target and dependencies. Require CPU as the only available GGML backend. Compare all execution-relevant cache options/compile flags across A/B/C; record only unavoidable source-revision differences. A predates the HINT/TRACE options and server compute-profile CLI; do not retrofit them or pass unknown options to A. B/C/D use TRACE OFF and `--server-compute-profile-mode legacy`, preserving the `llama_decode()` path. A uses its original `llama_decode()` path without that new flag. No auto/phase compute-profile experiment is part of this protocol.

Capture clean source HEADs, source status, generated build-info commit, ELF build IDs, SHA-256 of all executable/DSO dependencies, and resolved `ldd`/RPATH identities after build and again after measurement. Reject stale build-info or cross-build library resolution. C and D must resolve exactly the same libraries. Keep sources/binaries immutable during the campaign and do not compile concurrently with measurement.

Preflight free space was approximately 1.75 GB; the existing entire development build occupies approximately 1.98 GB. The future Release/server-only artifact sizes are not established yet. Step 10.2 must check capacity before each build and leave at least 512 MiB free after all builds/results allocation. Stop for insufficient capacity; do not delete existing trees or reuse uncertified binaries merely to fit. No cleanup or build is authorized by this document alone.

## Server and scheduling conditions

Use one local server at a time, one slot, CPU-only execution, no other server traffic, draft model, multimodal input, adapter, external contention, speculative decoding or changed compute profile. Keep mmap defaults and KV types unchanged between revisions; record effective startup configuration. Use UID 1000 for A/B/C servers and D launcher/server, nice 0. Root loader and normal-user launcher remain raw policy 0. Do not use phase TRACE, verbose diagnostic tracing, per-token timings, extra probes, or BPF phase polling during measurement.

For every server, the common arguments are:

```text
-m /home/codinghuman/projects/model.gguf
--host 127.0.0.1 --port 8096
--n-gpu-layers 0 --threads 6 --threads-batch 6 --threads-http 2
--ctx-size 2048 --parallel 1 --batch-size 512 --ubatch-size 256
--flash-attn off --no-ui
```

Six compute threads match six physical cores and avoid the old logical-thread oversubscription experiment. Batch threads are explicitly six as well, rather than an inherited/default value. HTTP threads are explicitly two. Pin with `taskset -c 0,2,4,6,8,10` before exec; verify all observed TID affinities and policies outside timed requests. Use one client, one non-streaming request at a time. Reserve loopback port 8096 before the campaign; stop rather than silently choose a new port if unavailable.

Launch from a controlled environment: remove inherited `LLAMA_ARG_*`, `GGML_*`, `OMP_*`, `OPENBLAS_*`, `MKL_*`, `LD_PRELOAD`, `LD_LIBRARY_PATH`, `CFLAGS` and `CXXFLAGS` overrides; set `OMP_NUM_THREADS=6` and `OMP_DYNAMIC=FALSE`. Leave other OpenMP tuning unset and record relevant environment/runtime library identity. Do not expose unrelated environment secrets in manifests. Keep client implementation, CPU affinity, JSON bytes, HTTP/1.1 connection policy and response handling equal across A/B/C/D. Use a fresh HTTP connection per request with `Connection: close`, no automatic retry, and a 180-second timeout.

For A/B/C, sched_ext must be disabled and all server TIDs must return raw policy 0. C still calls its HINT marker but has no attached scheduler uprobe.

For D, use the frozen loader/launcher and exactly C's server/marker paths. The root command, executed later through the established human privilege bridge or an explicitly authorized equivalent supervisor, is conceptually:

```bash
sudo taskset -c 1 /home/codinghuman/projects/llama.cpp-lightweight/tools/sched_ext/build/bin/llama_scx \
  --phase-uid 1000 --phase-register-socket "@$SOCKET_NAME" \
  --server-exe "$C_BUILD/bin/llama-server" \
  --marker-elf "$C_BUILD/bin/libllama-server-impl.so"
```

The existing loader embeds the absolute BPF-object path under `tools/sched_ext/build/`; verify that object hash. There is no new object-path CLI. Choose `SOCKET_NAME=llama_scx_step10_<run-id>_<visit-id>` with total abstract name length below 108 bytes. The normal-user command uses the validated one-shot registration launcher:

```bash
taskset -c 0,2,4,6,8,10 /home/codinghuman/projects/llama.cpp-lightweight/tools/sched_ext/build/bin/llama_scx_child \
  --phase-register-socket "@$SOCKET_NAME" -- "$C_BUILD/bin/llama-server" \
  -m /home/codinghuman/projects/model.gguf --host 127.0.0.1 --port 8096 \
  --n-gpu-layers 0 --threads 6 --threads-batch 6 --threads-http 2 \
  --ctx-size 2048 --parallel 1 --batch-size 512 --ubatch-size 256 \
  --flash-attn off --no-ui --server-compute-profile-mode legacy
```

Require registration ACK and the two established registration log messages. Verify loader/launcher raw policy 0, selected server/all observed TIDs raw policy 7. Keep exactly one PID-scoped entry phase uprobe, no external phase observer, no map reads or instrumentation during requests. Retain the loader's existing coarse lifecycle check. Root-only control is outside request timing; never require noninteractive sudo or ask for a password. A bounded supervisor may be a safety backstop, not the expected termination mechanism.

## Exact workload

POST only to `http://127.0.0.1:8096/completion`, with `Content-Type: application/json`. The canonical prompt below is specified by immutable ASCII text and deterministic construction; this avoids unrecorded random prompts. Repeating the same notes is intentional. The construction is offline preparation, not a runner or inference operation:

```python
base = "A small public library stands beside the town square. Its shelves hold stories, science books, travel guides, and local history. Every morning the librarian opens the windows, checks returned books, and prepares a quiet room for readers. Children visit after school to choose books and ask questions. Older residents use newspapers and share memories of the town. Visitors find maps and learn about nearby walking routes. A reading group meets once a week. Each person explains one idea from a book and listens to the other readers. The library supports curiosity, patient learning, and friendly conversation."
prompt = "Read the following notes and continue with a concise description of the library.\n\n" + "\n\n".join([base] * 8) + "\n\nContinue this sentence: The library is useful because"
request = {
    "prompt": prompt,
    "n_predict": 128,
    "temperature": 0,
    "seed": 424242,
    "stream": False,
    "cache_prompt": False,
    "ignore_eos": True,
    "id_slot": 0,
    "n_cache_reuse": 0,
    "stop": [],
    "return_tokens": False,
    "timings_per_token": False,
}
# prompt.txt has exactly prompt.encode("utf-8"), with no trailing newline.
# request.json has json.dumps(request, sort_keys=True, separators=(",", ":"),
#                             ensure_ascii=True) + "\n", encoded as UTF-8.
```

`prompt.txt`: 5023 bytes, 789 whitespace-separated words, SHA-256 **`b7be51379d30270d4d645aefb6014525e89e2bcba6e4be60f5f5613efbe5b4a9`**. Canonical `request.json`: 5243 bytes, SHA-256 **`7b68e4809a1f9bca18c2bc29b87c62c637e19e2ccd3785745cc717c046999e1d`**.

The planned scale is roughly 1000 prompt tokens and exactly 128 output tokens, comfortably within context 2048. Exact model-token count is not claimed from text alone. Before any measured request, the future runner must establish the count from normal warm-up results, require it to be in 512..1536 inclusive, and require identical `tokens_evaluated` and `timings.prompt_n` for every request/configuration. If the fixed text lies outside that range or counts differ, stop for a protocol amendment; do not tune the prompt after viewing performance. Do not add a chat template. The 128-token bound, empty stop list and `ignore_eos=true` prevent variable EOS termination. Require 128 generated tokens, finite positive prompt/decode timings, nonempty response, HTTP 200, no truncation, and `timings.cache_n=0`. `cache_prompt=false` bypasses common-prefix reuse in both inspected revisions. Each request recomputes the full prompt; do not accept cache-hit-only prefill.

## Repetition, lifecycle and deterministic order

Use **10 measured requests per configuration**, 40 total. Each visit starts one fresh server, performs **two excluded warm-up requests of the exact workload**, then performs **one measured request**, and shuts down that server. Because configs are interleaved and only one server may run, there are two warm-ups per visit (20 per config, 80 total), not just two per entire campaign. This equal rule establishes initialized graphs/threadpools and warm model pages after every process restart without accepting KV prompt reuse. Never include startup/load/warm-up/cooldown in measured request duration.

Before each visit, require previous server/launcher/loader gone, free port, sched_ext disabled and no remaining project BPF state. Start the next configuration only after that cleanup. For D, normal target SIGTERM -> launcher reap -> loader pidfd cleanup must complete; allow natural BPF teardown up to 2000 ms after loader exit, saving observations before checking. No explicit BPF deletion. A failure aborts the campaign and preserves evidence.

Measured order consists of 10 four-config blocks, using left rotation of ABCD by `(block_number - 1) % 4`:

| Block | Visit order |
| --- | --- |
| 1 | A B C D |
| 2 | B C D A |
| 3 | C D A B |
| 4 | D A B C |
| 5 | A B C D |
| 6 | B C D A |
| 7 | C D A B |
| 8 | D A B C |
| 9 | A B C D |
| 10 | B C D A |

Each config occurs once per block and 10 times overall; its position counts differ by at most one. Persist the complete 40-visit order before starting, including two warm-ups then one measurement per visit. Use IDs `b01-v1-A` through the prescribed last visit, not an unrecorded shuffle. Preserve block identity for paired variability analysis. No thread-count, prompt-size, co-load or compute-profile sweep is part of the primary comparison.

## Thermal, frequency and background conditions

Use AC mains connected for the whole campaign. Retain the inspected `acpi-cpufreq` driver, `schedutil` governor on all policies and boost enabled (`cpufreq/boost=1`). Do not change governors, frequency limits, boost, SMT, fan policy or system power settings. Record min/max/current frequency interfaces before/after each measured request; instantaneous readings are observations, not proof of equal effective clock rates. Boost can make current readings exceed nominal metadata. Frequency/scheduling interaction is part of the neutral-base comparison and must not be corrected away selectively.

Read CPU temperature by hwmon name `k10temp`, label `Tctl` (currently hwmon3/temp1_input), locating by name/label rather than relying on the hwmon number. Record sensor availability, AC state, governor/driver/boost, CPU online/allowed set, load averages, `/proc/stat` idle/busy deltas, memory availability and swap state. Read these only at bounded preparation/checkpoints, not through a persistent metrics process during the timed POST.

Before every block, require no build, model download, other llama-server/loader, perf, stress workload or known busy background job; inspect a bounded process CPU snapshot. Require one-minute load average <= 1.0 and aggregate CPU busy <= 5% over a five-second idle observation. Before the measured request, after the two warm-ups, require three readings five seconds apart with Tctl <= **55 C**, temperature range <= **2 C**, and aggregate busy <= **5%** in both five-second intervals. Aggregate busy is `100 * (1 - delta(idle+iowait)/delta(total))` using the first eight `/proc/stat` CPU counters, avoiding double-counted guest time. During this preparation only the ready server's normal idle activity is permitted.

Allow a maximum **180-second** cooldown/readiness window, polling every five seconds. If it does not settle, pause/abort the campaign; do not add warm-ups, relax limits, or choose a more favorable run. CPU temperature/frequency/load and AC/governor checks are saved immediately before and after measured requests. Missing Tctl/required interfaces or changed AC/governor/boost/CPU/kernel state makes the campaign unsuitable for the frozen primary comparison. Available hardware throttle counters may be recorded; do not assume unavailable counters exist or infer throttling solely from frequency variation. Keep terminal/browser traffic and background services stable; do not modify unrelated services.

Readiness violations occur before timing and therefore do not select on measured speed. Preserve all issued requests. A post-request policy/identity/configuration/count/error violation invalidates its entire four-config block and aborts the primary campaign; any repeat must be a separately authorized whole campaign with the same protocol. Retain the incomplete/invalid results. Do not discard statistical outliers or rerun only a slow D sample.

## Metrics and statistics

Use normal non-streaming server response fields, present in both revisions:

| Metric | Source | Direction |
| --- | --- | --- |
| Prefill throughput, tokens/s | `timings.prompt_per_second` | Higher is faster |
| Decode throughput, tokens/s | `timings.predicted_per_second` | Higher is faster |
| Total request duration, ms | External monotonic client clock, `request_wall_ms` | Lower is faster |

Start `time.perf_counter_ns()` immediately before sending the prepared POST and stop after reading the entire response body, before JSON decoding/result-file writes. Request construction, readiness checks and logging are outside the interval. This external client interval includes connection/HTTP/queue/tokenization/response costs and excludes server startup. It adds no scheduler/model timing hook. Record the counter implementation/resolution; keep it identical for all requests. Cross-check normal `prompt_ms`, `predicted_ms`, `prompt_n`, `predicted_n`, `cache_n`, `tokens_evaluated`, `tokens_predicted`, stop type, truncation, and response/content hash. The sum `prompt_ms+predicted_ms` is a server processing cross-check, **not** a substitute for whole-request duration. Keep full response JSON and normal stdout/stderr. Do not enable libllama diagnostic perf timing, phase TRACE, per-token timestamps or queue/worker accounting.

For each config/metric, use all 10 valid measured requests and report n, median, minimum, maximum, Q1, Q3, IQR and MAD. Q1/Q3 use linear interpolation at fractional position `(n-1)*p` in sorted samples (p=0.25/0.75); IQR=Q3-Q1; MAD=median(abs(sample-median)). Warm-ups are preserved and labeled but excluded.

For each A -> B, B -> C and C -> D pair, primary relative raw delta is:

```text
delta_pct = 100 * (median_candidate - median_reference) / median_reference
```

For throughput, positive delta means faster; for duration, positive delta means slower. Gate on signed slowdown, expressed so that positive always means slower:

```text
duration_slowdown_pct   = 100 * (median_candidate / median_reference - 1)
throughput_slowdown_pct = 100 * (median_reference / median_candidate - 1)
```

Throughput slowdown is the reciprocal-rate equivalent-duration change, not simply the negated throughput delta. Report both raw delta and slowdown. Never offset a prefill/decode regression with an improvement in another metric. Report the same per-block paired deltas as a cross-check; the primary estimate remains the ratio of configuration medians.

Also calculate a paired-block bootstrap 95% percentile interval for each slowdown: resample the 10 whole blocks with replacement 10000 times using Python `random.Random(20261006)`; recompute the ratio of medians each time; percentile endpoints 0.025/0.975 use the same linear interpolation convention. Preserve the four-config block associations, seed and analysis version. This is offline statistics, not new workload. If a 95% interval spans both <=0.5% and >1.0% categories, label precision inconclusive and require investigation/repeat even when the point estimate is small. Report intervals and spread; do not present a tiny median difference as resolved overhead when variability prevents that conclusion.

## Decision gate fixed before results

Apply the following primarily to B -> C and C -> D, using the worst signed median slowdown among prefill, decode and total duration for each pair:

| Slowdown | Required conclusion/action |
| --- | --- |
| <= 0.5% | Acceptable neutral overhead, subject to the frozen validity/precision checks |
| > 0.5% and <= 1.0% | Repeat/variance investigation required before judgment |
| > 1.0% | Mandatory overhead investigation before freezing Lightweight Base v1 |

A -> B is reported separately as the fork/base implementation delta; it is not attributed to sched_ext. Accept the infrastructure only when both B -> C and C -> D satisfy the gate. Negative slowdown denotes improvement, not evidence of a phase-aware optimization. Do not cherry-pick samples, optimize before measurements, or rename C -> D to framework overhead. Further experiments, reruns or implementation changes need later authorization.

## Future result artifact schema

Use the existing ignored `/benchmark-results/` convention, not the tracked archived experiment:

```text
/home/codinghuman/projects/llama.cpp-lightweight/benchmark-results/step10/<UTC-run-id>/
  manifest.json
  protocol.md
  machine-start.json
  machine-end.json
  workload/prompt.txt
  workload/request.json
  order.json
  builds/A/{identity.json,CMakeCache.txt,compile_commands.json,configure.log,build.log}
  builds/B/{identity.json,CMakeCache.txt,compile_commands.json,configure.log,build.log}
  builds/C/{identity.json,CMakeCache.txt,compile_commands.json,configure.log,build.log}
  builds/D-scheduler-identity.json
  raw/<visit-id>/
    command.json
    registration.json             # D only
    policies-before.json
    readiness.jsonl
    system-before.json
    warmup-1-response.json
    warmup-2-response.json
    measured-response.json
    measured-client.json
    system-after.json
    policies-after.json
    server.stdout.log
    server.stderr.log
    loader.log                    # D only
    cleanup.json
  summary/per-run.csv
  summary/config-summary.csv
  summary/deltas.csv
  summary/statistics.json
  commands.jsonl
```

Run ID is UTC `YYYYMMDDTHHMMSSZ` with an optional numeric collision suffix; persist it once. Manifest contains protocol document commit/hash, source tag resolutions, model identity, build IDs/hashes, scheduler hashes, kernel/BTF identity, workload hashes, CPU/thread/affinity policy, environment policy, fixed order, readiness limits, metric definitions, validity rules and campaign status. D's identity explicitly references C's hashes. Each raw record links block, visit position, config, warm-up/measured role, HTTP status, exact request hash, raw normal timings, external duration, process identities/policies/affinities and errors. CSV rows include all per-run metric values; summaries carry n/spread/intervals and gate outcome. All raw observations precede assertions; preserve failed/incomplete campaigns and administrative command stderr as well.

Store binaries/models once at their source paths and reference their hashes; do not duplicate them in results. Do not commit generated results or build artifacts. No Step 10.1 result directory, performance result, runner or build is created. No tag is created for this protocol step.
