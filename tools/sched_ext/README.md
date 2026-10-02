# llama.cpp sched_ext research component

This subtree is an optional Linux sched_ext research component. The main
llama.cpp project remains MIT-licensed. Files derived from Linux
`sched_ext/scx_simple` and the scheduler component are GPL-2.0 and are
intentionally kept inside this separately licensed subtree.

The privileged sched_ext loader will remain a separate executable from
`llama-server`. `llama-server` must remain runnable as a normal user and must
not link libbpf or privileged scheduler-loading functionality.

The normal llama.cpp build must not require:

- Linux sched_ext
- libbpf
- bpftool
- kernel headers
- kernel BTF
- root privileges

This Step 3 commit contains only repository structure and provenance. It does
not yet contain the project scheduler implementation. The current validated
implementation remains recoverable from:

- repository: https://github.com/codinghuman0/llama-scheduler
- local golden tag: `validation-scheduler-baseline-v1`
- exact commit: `ffc03c82738e31977cf402061422b0ef0148fe67`

The future integration sequence is:

```text
validated scheduler import
    -> one-repository golden validation
    -> minimal phase transport
    -> observer-effect removal
    -> lightweight neutral scheduler
    -> performance baseline
    -> scheduling policies
```

`provenance/linux-v6.17/` contains unmodified historical Linux source copies.
These files must not be edited as part of the project scheduler. Future active
scheduler sources will live directly under `tools/sched_ext/` and must not
modify the provenance copies in place.

The MIT llama-server side and GPL scheduler side will not share a GPL-only ABI
header. During the initial refactor, they will keep separately licensed,
matching declarations. Numeric and layout equivalence will be validated by
compile-time assertions and/or tests.
