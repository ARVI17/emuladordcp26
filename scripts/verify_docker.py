"""Run destructive tests only in a fresh local Compose project; never deploy the main stack."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import uuid
import signal
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from docker_lifecycle import HostLock, cleanup, prepare, recover, run_interruptible, save_manifest


def validate(config, project):
    if not project.startswith('emuladordcp26-check-') or config.get('name') != project:
        raise RuntimeError('Unexpected verification project')
    if config.get('volumes') or any(n.get('external') for n in config.get('networks', {}).values()):
        raise RuntimeError('Persistent volumes or external networks are forbidden in verification')
    for name, service in config['services'].items():
        if service.get('container_name') or service.get('network_mode') or service.get('privileged'):
            raise RuntimeError('Container identity/network must be isolated')
        for mount in service.get('volumes', []):
            allowed = {str((ROOT/'nginx/nginx.conf').resolve()), str((ROOT/'frontend/test-results').resolve())}
            if mount['type'] != 'bind' or str(Path(mount['source']).resolve()) not in allowed:
                raise RuntimeError('Unexpected test mount')
        for port in service.get('ports', []):
            if port.get('host_ip') != '127.0.0.1':
                raise RuntimeError('Verification ports must stay on loopback')
    for name in ('database', 'test-database'):
        if '/var/lib/postgresql/data' not in config['services'][name].get('tmpfs', []):
            raise RuntimeError('Test PostgreSQL must use disposable tmpfs')
    expected = 'postgresql+psycopg://planner_test:planner_test_only@test-database:5432/planner_unit_test'
    if config['services']['backend-test']['environment'].get('TEST_DATABASE_URL') != expected:
        raise RuntimeError('Unexpected destructive test database')
    api_db = 'postgresql+psycopg://planner_test:planner_test_only@database:5432/planner_review_test'
    if config['services']['backend']['environment'].get('DATABASE_URL') != api_db:
        raise RuntimeError('Unexpected API database')


def verify():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=['full', 'backend', 'frontend'], default='full')
    parser.add_argument('--pytest-path', action='append', default=[], help='Focused test file under backend/tests; omit for the full suite')
    parser.add_argument('--browser-spec', action='append', default=[], help='Focused spec under frontend/e2e; omit for all browser tests')
    parser.add_argument('--build-environment', choices=['test', 'local'], default='test',
                        help='Image provenance only; both choices use disposable isolated services and never deploy the main stack')
    parser.add_argument('--port', type=int, default=8082)
    args = parser.parse_args()
    for prefix, selected, extension in [('backend/tests', args.pytest_path, '.py'), ('frontend/e2e', args.browser_spec, '.spec.ts')]:
        root = (ROOT/prefix).resolve()
        for name in selected:
            candidate = (ROOT/prefix/name).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_file() or not name.endswith(extension):
                parser.error('Selected test must be an existing file inside '+prefix)
    if not 1024 <= args.port <= 65535 or args.port in {8080, 8081, 55432}:
        parser.error('Choose a separate unprivileged port (default 8082)')
    project = 'emuladordcp26-check-' + uuid.uuid4().hex[:10]
    report_dir = ROOT/'state/sprints'/project
    report_dir.mkdir(parents=True)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip())
    env = dict(os.environ, VERIFY_BACKEND_IMAGE=project+'-backend', REVIEW_PORT=str(args.port),
               BUILD_REVISION=revision, BUILD_DIRTY=str(dirty).lower(), BUILD_ENVIRONMENT=args.build_environment,
               BUILD_DATE=datetime.now(timezone.utc).isoformat())
    empty_env = report_dir/'empty.env'
    empty_env.write_text('', encoding='utf-8')
    context = subprocess.check_output(['docker', 'context', 'show'], text=True).strip()
    detail = json.loads(subprocess.check_output(['docker', 'context', 'inspect', context], text=True))[0]
    if not detail['Endpoints']['docker']['Host'].startswith(('npipe://', 'unix://')):
        raise RuntimeError('Select a local Docker engine before verification')
    docker = ['docker', '--context', context]
    recover(docker, context)
    compose = docker + ['compose', '--env-file', str(empty_env), '-p', project, '-f', 'docker-compose.review.yml', '-f', 'docker-compose.verify.yml']
    config = json.loads(subprocess.check_output(compose+['--profile', 'test', 'config', '--format', 'json'], cwd=ROOT, env=env, text=True))
    validate(config, project)
    manifest_path, manifest = prepare(config, project, context)
    effective = report_dir/'compose.json'
    effective.write_text(json.dumps(config, indent=2), encoding='utf-8')
    compose = docker + ['compose', '--env-file', str(empty_env), '-p', project, '-f', str(effective)]
    main_ids = subprocess.check_output(docker+['ps', '-aq', '--filter', 'label=com.docker.compose.project=emuladordcp26'], text=True).split()
    def main_state():
        if not main_ids: return []
        return [(c['Id'], c['State']['Status'], c['State']['StartedAt']) for c in json.loads(subprocess.check_output(docker+['inspect', *main_ids], text=True))]
    before = main_state()
    volumes_before = subprocess.check_output(docker+['volume', 'ls', '-q'], text=True).split()
    result = {'project': project, 'scope': args.scope, 'selected_pytest': args.pytest_path or 'all', 'selected_browser': args.browser_spec or 'all', 'git_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'steps': [], 'status': 'FAILED'}
    def step(name, *arguments):
        started = time.monotonic()
        with (report_dir/(name+'.log')).open('wb') as log:
            code = run_interruptible(compose+list(arguments), cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        result['steps'].append({'name': name, 'exit': code, 'seconds': round(time.monotonic()-started, 2)})
        print(name, 'PASSED' if code == 0 else 'FAILED', flush=True)
        if code: raise RuntimeError(f'{name} failed; see {report_dir/name}.log')
    try:
        step('build', 'build', 'backend', 'frontend', 'frontend-test', 'frontend-e2e')
        step('startup', 'up', '-d', '--wait', '--wait-timeout', '120', 'database', 'test-database', 'backend', 'frontend', 'nginx')
        for path in ('/health', '/api/openapi.json'):
            with urllib.request.urlopen(f'http://127.0.0.1:{args.port}{path}', timeout=10) as response:
                if response.status != 200: raise RuntimeError('HTTP verification failed')
        def metadata(path):
            with urllib.request.urlopen(f'http://127.0.0.1:{args.port}{path}', timeout=10) as response:
                return json.load(response)
        front, back = metadata('/build.json'), metadata('/api/build')
        if front != back or back['revision'] != revision or back['source_dirty'] != dirty:
            raise RuntimeError('Served build provenance does not match the tested source')
        result['served_build'] = back
        step('migration-current', 'exec', '-T', 'backend', 'alembic', 'current')
        step('migration-check', 'exec', '-T', 'backend', 'alembic', 'check')
        if args.scope in {'full', 'backend'}: step('pytest', 'run', '--rm', '--no-deps', 'backend-test', *['tests/'+p for p in args.pytest_path])
        if args.scope in {'full', 'frontend'}:
            step('vitest', 'run', '--rm', '--no-deps', 'frontend-test')
            step('playwright', 'run', '--rm', '--no-deps', 'frontend-e2e', *(['npm','run','test:e2e','--',*args.browser_spec] if args.browser_spec else []))
        result['status'] = 'PASSED'
    finally:
        # Finish owned cleanup even if the user presses Ctrl+C a second time.
        previous = {s: signal.signal(s, signal.SIG_IGN) for s in (signal.SIGINT, signal.SIGTERM)}
        if result['status'] != 'PASSED':
            with (report_dir/'services.log').open('wb') as log:
                try:
                    subprocess.run(compose+['logs', '--no-color', '--tail', '120'], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=20)
                except subprocess.TimeoutExpired:
                    pass
        try:
            cleanup(docker, manifest)
            save_manifest(manifest_path, manifest)
            result['steps'].append({'name': 'cleanup', 'exit': 0})
        except Exception:
            result['status'] = 'FAILED'
            raise
        finally:
            result['main_stack_unchanged'] = main_state() == before
            result['volumes_unchanged'] = subprocess.check_output(docker+['volume', 'ls', '-q'], text=True).split() == volumes_before
            if not result['main_stack_unchanged'] or not result['volumes_unchanged']: result['status'] = 'FAILED'
            (report_dir/'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print('Report:', report_dir/'result.json', flush=True)
            for signum, handler in previous.items(): signal.signal(signum, handler)
    if result['status'] != 'PASSED': raise RuntimeError('Verification failed')


def main():
    def cancelled(signum, frame):
        raise KeyboardInterrupt('Verificación cancelada')
    signal.signal(signal.SIGTERM, cancelled)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, cancelled)
    with HostLock():
        verify()


if __name__ == '__main__':
    main()
