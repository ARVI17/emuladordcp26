import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('verify_docker', ROOT/'scripts/verify_docker.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class IsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = 'emuladordcp26-check-guard-test'
        cls.config = json.loads(subprocess.check_output([
            'docker', 'compose', '-p', cls.project, '-f', 'docker-compose.review.yml', '-f', 'docker-compose.verify.yml',
            '--profile', 'test', 'config', '--format', 'json'], cwd=ROOT,
            env=dict(os.environ, VERIFY_BACKEND_IMAGE=cls.project+'-backend'), text=True))

    def test_real_test_configuration_is_isolated(self):
        verify.validate(self.config, self.project)

    def test_rejects_main_database_for_destructive_tests(self):
        config = copy.deepcopy(self.config)
        config['services']['backend-test']['environment']['TEST_DATABASE_URL'] = 'postgresql://database/fc26'
        with self.assertRaises(RuntimeError): verify.validate(config, self.project)

    def test_rejects_persistent_volume(self):
        config = copy.deepcopy(self.config)
        config['volumes'] = {'data': {'external': True, 'name': 'emuladordcp26_postgres_data'}}
        with self.assertRaises(RuntimeError): verify.validate(config, self.project)

    def test_rejects_unexpected_host_mount(self):
        config = copy.deepcopy(self.config)
        config['services']['backend']['volumes'] = [{'type': 'bind', 'source': str(ROOT/'backups'), 'target': '/backups'}]
        with self.assertRaises(RuntimeError): verify.validate(config, self.project)

    def test_rejects_main_project_and_public_port(self):
        with self.assertRaises(RuntimeError): verify.validate(self.config, 'emuladordcp26')
        config = copy.deepcopy(self.config)
        config['services']['nginx']['ports'][0]['host_ip'] = '0.0.0.0'
        with self.assertRaises(RuntimeError): verify.validate(config, self.project)


if __name__ == '__main__':
    unittest.main()
