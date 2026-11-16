"""Provenance/absence checks: diagnostics must never invent a pass or expose Docker env."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import project_status as status


class PlanTests(unittest.TestCase):
    def test_repository_plan_and_generated_view_agree(self):
        self.assertEqual(status.render_plan(status.load_plan(ROOT)), (ROOT/status.RENDER).read_text(encoding='utf-8'))

    def test_invalid_dependencies_states_and_missing_evidence_are_rejected(self):
        base = json.loads((ROOT/status.PLAN).read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'docs').mkdir()
            (root/'evidence.md').write_text('Synthetic evidence', encoding='utf-8')
            for item in base['items']:
                item['evidence'] = ['evidence.md']
            variants = []
            cyclic = copy.deepcopy(base)
            cyclic['items'][0]['depends_on'] = [cyclic['items'][0]['id']]
            variants.append(cyclic)
            unknown = copy.deepcopy(base)
            unknown['items'][0]['depends_on'] = ['NO-999']
            variants.append(unknown)
            bad_state = copy.deepcopy(base)
            bad_state['items'][0]['implementation'] = 'magically_complete'
            variants.append(bad_state)
            missing = copy.deepcopy(base)
            missing['items'][0]['evidence'] = ['missing.py']
            variants.append(missing)
            for value in variants:
                with self.subTest(value=value['items'][0]):
                    (root/status.PLAN).write_text(json.dumps(value), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        status.load_plan(root)


class ReportTests(unittest.TestCase):
    def report(self, root, name, value, timestamp):
        path = root/'state/sprints'/('emuladordcp26-check-'+name)/'result.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(value), encoding='utf-8')
        os.utime(path, (timestamp, timestamp))
        return path

    def base(self):
        return {'git_sha': 'a'*40, 'scope': 'full', 'status': 'PASSED',
                'selected_pytest': 'all', 'selected_browser': 'all',
                'main_stack_unchanged': True, 'volumes_unchanged': True,
                'served_build': {'source_dirty': False},
                'steps': [{'name': n, 'exit': 0} for n in ('build', 'startup', 'migration-current', 'migration-check',
                                                        'pytest', 'vitest', 'playwright', 'extension', 'cleanup')]}

    def test_latest_failure_does_not_hide_previous_pass_or_become_full_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.report(root, 'full', self.base(), 100)
            failed = self.base()
            failed.update(status='FAILED', git_sha='b'*40)
            failed['steps'][4]['exit'] = 1
            self.report(root, 'failed', failed, 200)
            result = status.reports(root)
            self.assertEqual(result['latest']['status'], 'FAILED')
            self.assertFalse(result['latest']['verified_pass'])
            self.assertEqual(result['latest_full_pass']['git_sha'], 'a'*40)

    def test_focused_full_scope_is_not_an_integral_run(self):
        with tempfile.TemporaryDirectory() as folder:
            value = self.base()
            value['selected_pytest'] = ['test_visual_scan.py']
            self.report(Path(folder), 'focused', value, 100)
            result = status.reports(Path(folder))
            self.assertTrue(result['latest']['verified_pass'])
            self.assertIsNone(result['latest_full_pass'])

    def test_missing_cleanup_or_isolation_prevents_pass_and_unknown_dirty_stays_unknown(self):
        for field in ('cleanup', 'main_stack_unchanged', 'volumes_unchanged'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                value = self.base()
                value.pop('served_build')
                if field == 'cleanup':
                    value['steps'] = value['steps'][:-1]
                else:
                    value.pop(field)
                self.report(Path(folder), 'incomplete', value, 100)
                result = status.reports(Path(folder))
                self.assertFalse(result['latest']['verified_pass'])
                self.assertIsNone(result['latest']['source_dirty'])

    def test_corrupt_report_and_empty_history_are_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertIsNone(status.reports(root)['latest'])
            path = self.report(root, 'corrupt', {}, 100)
            path.write_text('{broken', encoding='utf-8')
            result = status.reports(root)
            self.assertIsNone(result['latest_full_pass'])
            self.assertEqual(result['invalid_reports'], 1)


class RuntimeTests(unittest.TestCase):
    def test_reference_expiry_is_reported_without_renewing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root/'backend/app/data/fc27_references.json'
            target.parent.mkdir(parents=True)
            original = json.dumps([
                {'status': 'documented', 'verified_at': '2000-01-01T00:00:00+00:00', 'valid_until': '2001-01-01T00:00:00+00:00'},
                {'status': 'pending_verification'},
                {'status': 'documented', 'verified_at': '2000-01-01T00:00:00', 'valid_until': '2001-01-01T00:00:00'}])
            target.write_text(original, encoding='utf-8')
            (target.parent/'fc27_variants.json').write_text(json.dumps({
                'observed_at': '2000-01-01T00:00:00Z', 'valid_until': '2001-01-01T00:00:00Z',
                'items': [['synthetic-1'], ['synthetic-2']], 'pending': {'synthetic-3': 'unknown'}}), encoding='utf-8')
            result = status.reference_freshness(root)
            self.assertEqual((result[0]['active'], result[0]['expired'], result[0]['pending']), (0, 1, 2))
            self.assertEqual(result[1]['status'], 'unknown')
            self.assertIsNone(result[1]['active'])
            self.assertEqual((result[2]['active'], result[2]['expired'], result[2]['pending']), (0, 2, 1))
            self.assertEqual(result[3]['status'], 'unknown')
            (target.parent/'fc27_formations.json').write_text(json.dumps({'items': {
                'test': {'validation_status': 'documented', 'observed_at': '2000-01-01T00:00:00Z', 'valid_until': '2001-01-01T00:00:00Z'},
                'missing': {'validation_status': 'pending_verification'}}}), encoding='utf-8')
            formation = status.reference_freshness(root)[3]
            self.assertEqual((formation['active'], formation['expired'], formation['pending']), (0, 1, 1))
            self.assertEqual(target.read_text(encoding='utf-8'), original)

    def container(self, host='127.0.0.1'):
        return {'Id': 'a'*64, 'Image': 'sha256:'+'b'*64,
                'Config': {'Env': ['PRIVATE=do-not-copy'], 'Labels': {'com.docker.compose.project': status.PROJECT,
                           'com.docker.compose.service': 'nginx'}},
                'State': {'Status': 'running', 'Health': {'Status': 'healthy'}, 'Log': 'do-not-copy'},
                'HostConfig': {'PortBindings': {'80/tcp': [{'HostIp': host, 'HostPort': '8090'}]}}}

    def responses(self, containers, endpoint='npipe://local'):
        return ['desktop', json.dumps([{'Endpoints': {'docker': {'Host': endpoint}}}]), 'a'*64, json.dumps(containers)]

    def test_remote_engine_is_not_inspected_or_contacted(self):
        with patch.object(status, 'command', side_effect=self.responses([], 'tcp://remote:2376')) as run, patch.object(status, 'public_json') as http:
            result = status.runtime(ROOT)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(run.call_count, 2)
        http.assert_not_called()

    def test_non_loopback_binding_is_not_contacted(self):
        with patch.object(status, 'command', side_effect=self.responses([self.container('0.0.0.0')])), patch.object(status, 'public_json') as http:
            result = status.runtime(ROOT)
        self.assertEqual(result['http'], 'not_checked_unsafe_binding')
        http.assert_not_called()

    def test_docker_secrets_are_not_serialized_and_no_mutation_command_is_used(self):
        with patch.object(status, 'command', side_effect=self.responses([self.container()])) as run, patch.object(status, 'public_json', side_effect=OSError()):
            result = status.runtime(ROOT)
        self.assertNotIn('do-not-copy', json.dumps(result))
        self.assertIsNone(result['builds_match'])
        self.assertIsNone(result['backend_build'])
        self.assertEqual(result['http'], 'unavailable')
        self.assertEqual([call.args[1][1] for call in run.call_args_list], ['context', 'context', '--context', '--context'])

    def test_duplicate_service_is_rejected_before_http(self):
        with patch.object(status, 'command', side_effect=self.responses([self.container(), self.container()])), patch.object(status, 'public_json') as http:
            with self.assertRaises(ValueError):
                status.runtime(ROOT)
        http.assert_not_called()

    def test_redirect_to_external_address_is_rejected(self):
        with self.assertRaises(ValueError):
            status.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.invalid/')

    def test_offline_report_never_invokes_docker_or_http(self):
        with patch.object(status, 'runtime') as run, patch.object(status, 'command', side_effect=['a'*40, 'test-branch', '']):
            value = status.snapshot(ROOT, include_runtime=False)
        run.assert_not_called()
        self.assertEqual(value['runtime']['status'], 'not_checked')


class LifecycleTests(unittest.TestCase):
    def test_verification_failure_still_refreshes_memory_without_hiding_error(self):
        spec = importlib.util.spec_from_file_location('continuity_verify_test', ROOT/'scripts/verify_docker.py')
        verify = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verify)
        for failure in (RuntimeError('test failure'), KeyboardInterrupt('cancelled')):
            with self.subTest(failure=type(failure).__name__), patch.object(verify, 'HostLock'), patch.object(verify.signal, 'signal'), patch.object(verify, 'verify', side_effect=failure), patch.object(status, 'write_status') as refresh:
                with self.assertRaises(type(failure)):
                    verify.main()
                refresh.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
