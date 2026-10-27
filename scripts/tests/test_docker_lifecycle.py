import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from docker_lifecycle import HostLock, OWNER, owned_container, prepare, published_ports


class LifecycleGuards(unittest.TestCase):
    def test_personal_ports_stay_reserved_when_containers_are_stopped(self):
        containers=[{'State':{'Running':False},'HostConfig':{'PortBindings':{'80/tcp':[{'HostPort':'8090'}],'443/tcp':None}}},
                    {'HostConfig':{'PortBindings':{'5432/tcp':[{'HostPort':'55432'}]}}},{}]
        self.assertEqual(published_ports(containers),{8090,55432})

    def test_lock_is_shared_across_processes_and_released(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'lock'
            code = "from docker_lifecycle import HostLock; import sys;\nwith HostLock(sys.argv[1]): print('acquired')"
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
            with HostLock(path):
                child = subprocess.run([sys.executable, '-c', code, str(path)], env=env, capture_output=True)
                self.assertNotEqual(child.returncode, 0)
            child = subprocess.run([sys.executable, '-c', code, str(path)], env=env, capture_output=True)
            self.assertEqual(child.returncode, 0, child.stderr)

    def test_cleanup_requires_identity_image_and_disposable_data(self):
        manifest = {'run': 'unique', 'project': 'emuladordcp26-check-unique', 'services': {'backend': {'image': 'owned:unique'}}}
        container = {'Config': {'Image': 'owned:unique', 'Labels': {OWNER: 'unique', OWNER+'.data': 'synthetic-disposable', 'com.docker.compose.project': manifest['project'], 'com.docker.compose.service': 'backend'}}, 'Mounts': [], 'HostConfig': {}}
        owned_container(container, manifest)
        for field, value in [('Image', 'other:tag'), ('Labels', {} )]:
            changed = copy.deepcopy(container)
            changed['Config'][field] = value
            with self.assertRaises(RuntimeError): owned_container(changed, manifest)
        changed = copy.deepcopy(container)
        changed['Mounts'] = [{'Type': 'volume', 'Source': 'personal', 'Destination': '/data', 'RW': True}]
        with self.assertRaises(RuntimeError): owned_container(changed, manifest)

    def test_build_tags_and_labels_belong_to_one_run(self):
        config = {'services': {'backend': {'build': {}}, 'backend-test': {'image': 'unsafe'}, 'frontend': {'build': {}}}, 'networks': {'default': {}}}
        with tempfile.TemporaryDirectory() as folder:
            path, manifest = prepare(config, 'emuladordcp26-check-unique', 'local', folder)
            self.assertEqual(config['services']['backend']['image'], config['services']['backend-test']['image'])
            self.assertNotEqual(config['services']['frontend']['image'], config['services']['backend']['image'])
            self.assertEqual(json.loads(path.read_text())['run'], 'unique')
            self.assertEqual(config['networks']['default']['labels'][OWNER], 'unique')
