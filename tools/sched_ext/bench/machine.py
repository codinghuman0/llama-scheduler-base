# SPDX-License-Identifier: GPL-2.0
"""Checkpoints run outside requests; there is no background observer."""
import os
from pathlib import Path
import re
import time

from common import BOOT_ID, command, require, topology, write_json


def snapshot():
    cpu = Path('/sys/devices/system/cpu')
    policies = {}
    for policy in sorted((cpu / 'cpufreq').glob('policy*')):
        policies[policy.name] = {key: (policy / key).read_text().strip() for key in
                                 ('scaling_driver', 'scaling_governor', 'scaling_cur_freq', 'scaling_min_freq', 'scaling_max_freq')}
    temperatures = []
    for hwmon in Path('/sys/class/hwmon').glob('hwmon*'):
        if (hwmon / 'name').read_text().strip() == 'k10temp':
            for label in hwmon.glob('temp*_label'):
                if label.read_text().strip() == 'Tctl':
                    temperatures.append(int(label.with_name(label.name.replace('_label', '_input')).read_text()) / 1000)
    ac = {p.parent.name: p.read_text().strip() for p in Path('/sys/class/power_supply').glob('*/online')}
    memory = {k: int(v) for k, v in re.findall(r'^(MemAvailable|SwapTotal|SwapFree):\s+(\d+)', Path('/proc/meminfo').read_text(), re.M)}
    return dict(kernel=os.uname().release, boot_id=BOOT_ID.read_text().strip(), topology=topology(),
                policies=policies, boost=(cpu / 'cpufreq/boost').read_text().strip(), ac=ac,
                tctl_c=temperatures[0] if len(temperatures) == 1 else None,
                loadavg=list(os.getloadavg()), memory_kib=memory,
                runner_affinity=sorted(os.sched_getaffinity(0)), monotonic_ns=time.monotonic_ns())


def invariants(value):
    return {key: value[key] for key in ('kernel', 'boot_id', 'topology', 'boost', 'ac')} | {
        'policies': {p: {k: v for k, v in fields.items() if k != 'scaling_cur_freq'} for p, fields in value['policies'].items()}}


def validate(value, baseline=None):
    require(value['policies'] and all(p['scaling_driver'] == 'acpi-cpufreq' and p['scaling_governor'] == 'schedutil' for p in value['policies'].values()), 'CPU governor/driver differs from frozen protocol')
    require(value['boost'] == '1' and value['ac'] and all(v == '1' for v in value['ac'].values()), 'AC/boost state unsuitable')
    require(value['tctl_c'] is not None, 'Tctl interface missing')
    if baseline:
        require(invariants(value) == invariants(baseline), 'Machine configuration changed during campaign')


def counters():
    values = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    return sum(values), values[3] + values[4]


def busy(before, after):
    total = after[0] - before[0]
    require(total > 0, 'CPU counter observation invalid')
    return 100 * (1 - (after[1] - before[1]) / total)


def reject_interactive_apps():
    rows = command(['ps', '-eo', 'pid=,comm=,pcpu=,args=']).splitlines()
    offenders = []
    for row in rows:
        fields = row.strip().split(None, 3)
        if len(fields) < 4 or int(fields[0]) == os.getpid():
            continue
        comm, _cpu, argv = fields[1:]
        comm = comm.lower()
        if comm.startswith(('firefox', 'codex')) or comm in {'stress-ng', 'perf', 'cmake', 'make', 'ninja', 'cc1', 'cc1plus', 'wget', 'curl'} or (comm in {'node', 'electron'} and re.search(r'(^|[/ .-])codex([/ .-]|$)', argv, re.I)):
            offenders.append(row.strip())
    require(not offenders, 'Close interactive/benchmark applications first: ' + '; '.join(offenders))
    return rows


def readiness(run, name, baseline, *, after_warmup):
    deadline = time.monotonic() + 180
    readings = []
    while time.monotonic() < deadline:
        first, sample1 = counters(), snapshot()
        validate(sample1, baseline)
        time.sleep(5)
        second, sample2 = counters(), snapshot()
        validate(sample2, baseline)
        record = dict(first=sample1, second=sample2, busy_pct=busy(first, second))
        if after_warmup:
            time.sleep(5)
            third, sample3 = counters(), snapshot()
            validate(sample3, baseline)
            record.update(third=sample3, second_busy_pct=busy(second, third))
            temps = [s['tctl_c'] for s in (sample1, sample2, sample3)]
            ready = max(temps) <= 55 and max(temps) - min(temps) <= 2 and max(record['busy_pct'], record['second_busy_pct']) <= 5
        else:
            ready = sample2['loadavg'][0] <= 1 and record['busy_pct'] <= 5
        record['ready'] = ready
        readings.append(record)
        write_json(run / name, readings)
        if ready:
            return
    raise RuntimeError('Readiness/cooldown did not settle within 180 seconds')
