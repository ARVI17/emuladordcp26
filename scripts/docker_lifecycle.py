"""Ownership and host-wide exclusion for disposable FC27 Docker tests."""
from contextlib import AbstractContextManager
import json
import os
from pathlib import Path
import subprocess

OWNER = 'io.fc27.verification'
STATE = Path.home()/'.fc27'/'verification'


class HostLock(AbstractContextManager):
    def __init__(self, path=STATE/'host.lock'):
        self.path = Path(path)

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open('a+b')
        if self.file.tell() == 0:
            self.file.write(b'0')
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise RuntimeError('Ya hay una verificación FC27 en curso en este host.') from exc
        return self

    def __exit__(self, *args):
        self.file.close()  # The OS releases the lock even after abrupt process termination.


def output(docker, *args):
    return subprocess.check_output([*docker, *args], text=True).strip()


def published_ports(containers):
    """Reserve the personal installation's configured ports even while stopped."""
    return {int(binding['HostPort']) for c in containers
            for bindings in (c.get('HostConfig', {}).get('PortBindings') or {}).values()
            for binding in bindings or [] if str(binding.get('HostPort', '')).isdigit()}


def owned_container(container, manifest):
    labels = container['Config'].get('Labels') or {}
    if labels.get(OWNER) != manifest['run'] or labels.get('com.docker.compose.project') != manifest['project']:
        raise RuntimeError('Propiedad de contenedor no acreditada; se conserva.')
    if labels.get(OWNER+'.data') != 'synthetic-disposable':
        raise RuntimeError('Datos no acreditados como desechables; se conserva.')
    service = labels.get('com.docker.compose.service')
    spec = manifest['services'].get(service)
    if not spec or container['Config']['Image'] != spec['image']:
        raise RuntimeError('Servicio o imagen ajenos; se conserva.')
    actual = {(m['Type'], m.get('Source'), m['Destination'], m['RW']) for m in container.get('Mounts', [])}
    expected = {('bind', m['source'], m['target'], not m.get('read_only', False)) for m in spec.get('volumes', [])}
    if actual != expected:
        raise RuntimeError('Montajes cambiados o persistentes; se conserva.')
    if service in {'database', 'test-database'} and '/var/lib/postgresql/data' not in (container['HostConfig'].get('Tmpfs') or {}):
        raise RuntimeError('Base de pruebas sin tmpfs; se conserva.')


def cleanup(docker, manifest):
    """Revalidate every full ID, then stop/remove only this run. Never remove volumes."""
    ids = output(docker, 'ps', '-aq', '--no-trunc', '--filter', 'label='+OWNER+'='+manifest['run']).split()
    containers = json.loads(output(docker, 'inspect', *ids)) if ids else []
    for c in containers:
        owned_container(c, manifest)
    for c in containers:
        # Avoid operating on a replacement by name or Compose's orphan matching.
        owned_container(json.loads(output(docker, 'inspect', c['Id']))[0], manifest)
        output(docker, 'stop', '--time', '20', c['Id'])
        output(docker, 'rm', c['Id'])
    networks = output(docker, 'network', 'ls', '-q', '--no-trunc', '--filter', 'label='+OWNER+'='+manifest['run']).split()
    for network in networks:
        detail = json.loads(output(docker, 'network', 'inspect', network))[0]
        if detail.get('Containers') or detail['Labels'].get('com.docker.compose.project') != manifest['project']:
            raise RuntimeError('Red compartida u ocupada; se conserva.')
        output(docker, 'network', 'rm', detail['Id'])
    manifest['status'] = 'cleaned'


def save_manifest(path, manifest):
    path = Path(path)
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    pending.replace(path)


def recover(docker, context, directory=STATE):
    """Called only under HostLock. A missing/mismatched manifest grants no authority."""
    ids = output(docker, 'ps', '-aq', '--filter', 'label='+OWNER).split()
    nets = output(docker, 'network', 'ls', '-q', '--filter', 'label='+OWNER).split()
    containers = json.loads(output(docker, 'inspect', *ids)) if ids else []
    networks = json.loads(output(docker, 'network', 'inspect', *nets)) if nets else []
    remaining = {c['Config']['Labels'][OWNER] for c in containers} | {n['Labels'][OWNER] for n in networks}
    known = set()
    for path in sorted(Path(directory).glob('run-*.json')):
        manifest = json.loads(path.read_text(encoding='utf-8'))
        if manifest['context'] == context:
            known.add(manifest['run'])
            # A daemon request can finish after the client was killed. Reinspect
            # owned remnants even when an earlier cleanup recorded success.
            if manifest['status'] != 'cleaned' or manifest['run'] in remaining:
                cleanup(docker, manifest)
                save_manifest(path, manifest)
    if remaining - known:
        raise RuntimeError('Hay restos sin manifiesto de propiedad; se conservan para revisión.')


def prepare(config, project, context, directory=STATE):
    run_id = project.removeprefix('emuladordcp26-check-')
    labels = {OWNER: run_id, OWNER+'.data': 'synthetic-disposable'}
    for name, service in config['services'].items():
        service.setdefault('labels', {}).update(labels)
        if 'build' in service:
            service['image'] = project+':'+name
    # backend-test shares exactly this run's immutable-by-name backend build.
    config['services']['backend-test']['image'] = config['services']['backend']['image']
    for network in config.get('networks', {}).values():
        network.setdefault('labels', {}).update(labels)
    manifest = dict(run=run_id, project=project, context=context, status='running',
                    services={n: {k: s[k] for k in ('image', 'volumes') if k in s} for n, s in config['services'].items()})
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory/('run-'+run_id+'.json')
    save_manifest(path, manifest)
    return path, manifest


def run_interruptible(command, **kwargs):
    """Stop the Compose client before finally cleans resources after Ctrl+C/SIGTERM."""
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    with subprocess.Popen(command, **kwargs, **options) as process:
        try:
            return process.wait()
        except BaseException:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise
