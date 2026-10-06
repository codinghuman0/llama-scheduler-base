# SPDX-License-Identifier: GPL-2.0
"""Synthetic and non-workload checks; never load BPF or send HTTP."""
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import analysis
import common
import machine
import root_helper
import step10


def response():
    return dict(content='synthetic fixture', truncated=False, stop_type='limit', tokens_evaluated=900,
                tokens_predicted=128, timings=dict(cache_n=0, prompt_n=900, predicted_n=128,
                prompt_per_second=100.0, predicted_per_second=20.0, prompt_ms=9000.0, predicted_ms=6400.0))


class CampaignTests(unittest.TestCase):
    def test_request_identity_and_order(self):
        self.assertEqual(len(common.PROMPT.encode()), 5023)
        self.assertEqual(hashlib.sha256(common.PROMPT.encode()).hexdigest(), common.PROMPT_SHA)
        self.assertEqual(hashlib.sha256(common.canonical(common.REQUEST)).hexdigest(), common.REQUEST_SHA)
        plans = common.order()
        self.assertEqual(len(plans), 40)
        self.assertEqual([''.join(p['config'] for p in plans[i:i+4]) for i in range(0,40,4)],
                         ['ABCD','BCDA','CDAB','DABC','ABCD','BCDA','CDAB','DABC','ABCD','BCDA'])
        for config in 'ABCD':
            self.assertEqual(sum(p['config'] == config for p in plans), 10)

    def test_affinity_and_d_bundle_identity(self):
        self.assertEqual(common.parse_cpus('0-2,4,6,8,10-11'), {0,1,2,4,6,8,10,11})
        self.assertEqual(sum(1 << cpu for cpu in common.SERVER_CPUS), 0x155)
        self.assertFalse(common.SERVER_CPUS & common.HOUSE_CPUS)
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            c, c_bundle = step10.server_argv(run, 'C')
            d, d_bundle = step10.server_argv(run, 'D')
            self.assertEqual(c, d)
            self.assertEqual(c_bundle, d_bundle)
            self.assertEqual(c[c.index('--threads')+1], '5')
            self.assertEqual(c[c.index('--threads-batch')+1], '5')
            a, _ = step10.server_argv(run, 'A')
            self.assertNotIn('--server-compute-profile-mode', a)

    def test_sanitized_environment(self):
        with patch.dict(os.environ, {'OMP_NUM_THREADS': '99', 'GOMP_CPU_AFFINITY': '1', 'LD_PRELOAD': 'bad', 'CMAKE_TOOLCHAIN_FILE': 'bad', 'CC': 'bad'}):
            env = common.bundle_env(Path('/tmp/fixture'))
            self.assertEqual(env['OMP_NUM_THREADS'], '5')
            self.assertEqual(env['LD_LIBRARY_PATH'], '/tmp/fixture/bin')
            for key in ('LD_PRELOAD', 'GOMP_CPU_AFFINITY', 'CMAKE_TOOLCHAIN_FILE', 'CC'):
                self.assertNotIn(key, env)

    def test_bundle_extraction_precedes_owned_build_removal(self):
        for config in 'ABC':
            with self.subTest(config=config), tempfile.TemporaryDirectory() as temp:
                run = Path(temp)
                events = []
                revision = common.REVISIONS[config]
                def fake_command(argv, **_kwargs):
                    if argv[:2] == ['git', 'rev-parse']:
                        return revision[:9] if '--short' in argv else revision
                    if argv[0] == 'nm':
                        return '00000001 T llama_scx_phase_v1'
                    return 'synthetic ELF identity'
                def fake_audit(_run, argv, **_kwargs):
                    events.append([str(a) for a in argv])
                    if argv[:3] == ['git','worktree','add']:
                        source = Path(argv[4])
                        (source / 'common').mkdir(parents=True)
                    elif argv[:3] == ['git','worktree','remove']:
                        shutil.rmtree(argv[4])
                    elif argv[0] == 'cmake' and '-S' in argv:
                        build = Path(argv[argv.index('-B')+1])
                        (build / 'bin').mkdir(parents=True)
                        (build / 'common').mkdir()
                        (build / 'common/build-info.cpp').write_text(revision[:9])
                        cache = '\n'.join(a[2:].split('=')[0]+':STRING='+a.split('=',1)[1] for a in argv if a.startswith('-D'))
                        (build / 'CMakeCache.txt').write_text(cache+'\nCMAKE_CXX_FLAGS_RELEASE:STRING=-O3 -DNDEBUG\n')
                        (build / 'compile_commands.json').write_text('["-march=native -O3 -DNDEBUG"]')
                        for name in ('llama-server','libllama-server-impl.so'):
                            (build / 'bin' / name).write_bytes(b'synthetic runtime bytes')
                        (build / 'bin/libllama.so.0.0.1').write_bytes(b'synthetic versioned library')
                        (build / 'bin/libllama.so.0').symlink_to('libllama.so.0.0.1')
                        (build / 'bin/libllama.so').symlink_to('libllama.so.0')
                    elif '--version' in argv:
                        self.assertTrue(Path(argv[-2]).exists())
                        self.assertEqual(argv[:3], ['/usr/bin/taskset', '-c', '0,2,4,6,8'])
                        self.assertTrue((run / '.prepare' / config / 'build').exists())
                        return revision[:9]
                    return ''
                def fake_dependencies(server, _env):
                    return 'synthetic ldd', [Path(server).parent / 'libllama-server-impl.so', Path(server).parent / 'libllama.so.0.0.1']
                with patch.object(step10,'audit_command',side_effect=fake_audit), patch.object(step10,'command',side_effect=fake_command), patch.object(step10,'dependencies',side_effect=fake_dependencies):
                    record = step10.build_bundle(run, config)
                self.assertEqual(record['revision'], revision)
                self.assertEqual(len(record['files']), 5)
                self.assertEqual(record['symlinks']['bin/libllama.so.0'], 'libllama.so.0.0.1')
                self.assertEqual((run / 'artifacts' / config / 'bin/libllama.so').read_bytes(), b'synthetic versioned library')
                self.assertFalse((run / '.prepare' / config).exists())
                version_index = next(i for i, e in enumerate(events) if '--version' in e)
                removal_index = next(i for i, e in enumerate(events) if e[:3] == ['git','worktree','remove'])
                self.assertLess(version_index, removal_index)

    def test_pointer_and_state_preserve_evidence(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(common, 'RESULTS', Path(temp)):
            root = Path(temp)
            run = root / '20261006T010203Z'
            run.mkdir()
            (root / '.active-run').write_text(run.name)
            self.assertEqual(common.active_run(), run)
            common.write_json(run / 'manifest.json', dict(status='PREPARED'))
            step10.change_status(run, 'FAILED', error='synthetic')
            self.assertEqual(common.read_json(run / 'manifest.json')['error'], 'synthetic')
            (run / 'evidence.json').write_text('retained')
            with common.locked(run):
                self.assertTrue((run / 'evidence.json').exists())
            (root / '.active-run').write_text('../../escape')
            with self.assertRaises(RuntimeError):
                common.active_run()

    def test_root_helper_whitelist(self):
        for op in root_helper.OPS:
            message = dict(op=op, token='secret')
            if op in {'START','STOP'}:
                message['visit'] = 4
            self.assertEqual(root_helper.validate_message(message, 'secret'), op)
        bad = [dict(op='EXEC', token='secret', command='id'), dict(op='HELLO', token='wrong'),
               dict(op='START', token='secret', visit=4, server_exe='/bin/sh'),
               dict(op='STOP', token='secret', visit=4, signal=9),
               dict(op='START', token='secret', visit=True), dict(op='START', token='secret', visit=41)]
        for message in bad:
            with self.assertRaises(RuntimeError):
                root_helper.validate_message(message, 'secret')
        helper = root_helper.Helper.__new__(root_helper.Helper)
        helper.child, helper.last, helper.manifest = None, None, dict(order=common.order())
        with patch.object(root_helper, 'state', return_value='disabled'):
            with self.assertRaisesRegex(RuntimeError, 'Only a frozen D visit'):
                helper.start(1)

    def test_bpf_classifier_ignores_unrelated_links(self):
        unrelated = dict(prog=[dict(id=1,name='system',type='kprobe')], map=[dict(id=2,name='system',type='hash')],
                         link=[dict(id=3,type='perf_event',prog_id=1), dict(id=4,type='struct_ops',map_id=2)])
        self.assertEqual(common.project_objects(unrelated), [])
        related = dict(prog=[dict(id=8,name='llama_phase',type='kprobe')], map=[dict(id=9,name='llama_sc.data',type='array')],
                       link=[dict(id=10,type='perf_event',prog_id=8)])
        self.assertEqual({p['id'] for p in common.project_objects(related)}, {8,9,10})

    def test_helper_prefers_natural_loader_exit(self):
        helper = root_helper.Helper.__new__(root_helper.Helper)
        helper.child = dict(visit=4, pidfd=123, identity={}, administrative_stop=False)
        helper.last = dict(visit=4, clean=True)
        with patch.object(root_helper.select, 'select', return_value=([123],[],[])), patch.object(helper, 'reap'), patch.object(root_helper, 'signal_exact') as send:
            result = helper.stop(4)
            send.assert_not_called()
            self.assertTrue(result['clean'])

    def test_snapshot_saved_before_teardown_assertion(self):
        baseline = dict(prog=[],link=[],map=[])
        persistent = dict(prog=[dict(id=8,name='llama_phase',type='kprobe')],link=[],map=[],sched_ext='disabled')
        with tempfile.TemporaryDirectory() as temp, patch.object(common, 'reduced_bpf', return_value=persistent), patch.object(common.time, 'sleep'), patch.object(common, 'state', return_value='disabled'):
            run = Path(temp)
            with self.assertRaisesRegex(RuntimeError, 'did not converge'):
                common.bpf_timeline(run, 'fixture', baseline, 0)
            self.assertEqual(len(list(run.glob('fixture-bpf-T*.json'))), 7)
            self.assertEqual(common.read_json(run / 'fixture-bpf-T0.json')['prog'][0]['id'], 8)

    def test_identity_safe_signal_and_reap(self):
        process = subprocess.Popen(['/usr/bin/sleep', '30'])
        try:
            saved = common.identity(process.pid)
            altered = saved | dict(starttime='wrong')
            with self.assertRaises(RuntimeError):
                common.signal_exact(altered, signal.SIGTERM)
            self.assertIsNone(process.poll())
            result = step10.stop_process(process, saved)
            self.assertEqual(result, -signal.SIGTERM)
            common.wait_gone(saved)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

    def test_request_validator(self):
        value = response()
        self.assertEqual(common.validate_response(value, 200), 900)
        for field, bad in (('cache_n', 1), ('predicted_n', 127), ('prompt_per_second', float('nan'))):
            altered = response()
            altered['timings'][field] = bad
            with self.assertRaises(RuntimeError):
                common.validate_response(altered, 200)
        with self.assertRaises(RuntimeError):
            common.validate_response(value, 200, 901)

    def test_frozen_statistics_and_reject_incomplete_blocks(self):
        rows = [p | dict(prefill_tps=100, decode_tps=20, request_wall_ms=1000) for p in common.order()]
        summary = analysis.summarize(rows)
        for name, pair in summary['pairs'].items():
            self.assertEqual(pair['gate'], 'reference_only' if name == 'A->B' else 'acceptable')
            for metric in pair['metrics'].values():
                self.assertEqual(metric['bootstrap_95_pct'], [0,0])
        self.assertEqual(analysis.percentile([1,2,3,4], 0.25), 1.75)
        self.assertAlmostEqual(analysis.slowdown(100, 99, 'prefill_tps'), 100/99*100-100)
        with self.assertRaises(RuntimeError):
            analysis.summarize(rows[:-1])

    def test_synthetic_stored_campaign_parser(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            (run / 'raw').mkdir()
            common.write_json(run / 'manifest.json', dict(order=common.order(), prompt_n=900))
            common.write_json(run / 'visit-order.json', common.order())
            artifact = dict(files={'bin/llama-server':'synthetic'}, revision='synthetic')
            common.write_json(run / 'artifacts.json', {c: artifact for c in 'ABC'})
            snapshot = dict(kernel='fixture',boot_id='fixture',topology={},boost='1',ac={'ADP0':'1'},tctl_c=40,
                            policies={'policy0':dict(scaling_driver='acpi-cpufreq',scaling_governor='schedutil')})
            common.write_json(run / 'machine.json', dict(before=snapshot))
            for plan in common.order():
                path = run / 'raw' / f"{plan['visit']:02d}-{plan['config']}"
                path.mkdir()
                common.write_json(path / 'visit.json', plan | dict(status='VALID',artifact_files=artifact['files'],request_sha256=common.REQUEST_SHA))
                common.write_json(path / 'command.json', dict(revision='synthetic',affinity=sorted(common.SERVER_CPUS),compute_threads=5,batch_threads=5,http_threads=2))
                common.write_json(path / 'cleanup.json', dict(status='PASS',server_launcher_exit=0,sched_ext='disabled',port_free=True,
                                                             root=dict(clean=True,loader_exit=0,loader_sigterm_requested=False,timeline=[dict(project_objects=[])])))
                for role in ('warmup-1','warmup-2','measured'):
                    common.write_json(path / f'{role}-response.json', response())
                    common.write_json(path / f'{role}-client.json', dict(role=role,http_status=200,request_sha256=common.REQUEST_SHA,
                                                                       response_sha256=common.sha(path / f'{role}-response.json'),request_wall_ms=1000))
                for name in ('before','pre-measured','after'):
                    common.write_json(path / f'policies-{name}.json', dict(tids=[dict(uid=1000,policy=7 if plan['config']=='D' else 0,affinity=sorted(common.SERVER_CPUS))],
                                                                        runner=dict(policy=0,affinity=[11]),launcher=dict(policy=0,uid=1000,affinity=[11]),loader=dict(policy=0,uid=0,affinity=[10])))
                for name in ('before','after'):
                    common.write_json(path / f'system-{name}.json', snapshot)
            rows = step10.collect_rows(run)
            self.assertEqual(len(rows), 40)
            analysis.export(run, rows, analysis.summarize(rows))
            self.assertTrue((run / 'final-report.md').exists())
            damaged = run / 'raw/04-D/visit.json'
            common.write_json(damaged, common.read_json(damaged) | dict(status='INVALID'))
            with self.assertRaises(RuntimeError):
                step10.collect_rows(run)


if __name__ == '__main__':
    unittest.main(verbosity=2)
