"""Opt-in real Docker checks of success/error/cancellation/crash cleanup; synthetic resources only."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid
from docker_lifecycle import HostLock, OWNER, STATE, cleanup, output, recover, save_manifest


def create(docker, context):
    run = uuid.uuid4().hex
    project = 'emuladordcp26-check-'+run
    manifest = dict(run=run, project=project, context=context, status='running', services={'worker': {'image': 'nginx:1.27-alpine'}})
    path = STATE/('run-'+run+'.json')
    save_manifest(path, manifest)
    labels = ['--label', OWNER+'='+run, '--label', OWNER+'.data=synthetic-disposable', '--label', 'com.docker.compose.project='+project]
    network = output(docker, 'network', 'create', *labels, project)
    cid = output(docker, 'run', '-d', '--network', network, *labels, '--label', 'com.docker.compose.service=worker', 'nginx:1.27-alpine', 'sleep', '120')
    return path, manifest, cid


def child(context):
    docker = ['docker', '--context', context]
    def cancelled(*args): raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, cancelled)
    if hasattr(signal, 'SIGBREAK'): signal.signal(signal.SIGBREAK, cancelled)
    path, manifest, cid = create(docker, context)
    try:
        print(json.dumps({'path': str(path), 'id': cid}), flush=True)
        if sys.stdin.readline().strip() == 'cancel':
            raise KeyboardInterrupt('Cancelación solicitada')
    finally:
        cleanup(docker, manifest)
        save_manifest(path, manifest)


def main():
    context = output(['docker'], 'context', 'show')
    docker = ['docker', '--context', context]
    detail = json.loads(output(docker, 'context', 'inspect', context))[0]
    assert detail['Endpoints']['docker']['Host'].startswith(('npipe://', 'unix://'))
    with HostLock():
        recover(docker, context)
        for outcome in ('success', 'error', 'late_finish'):
            path, manifest, cid = create(docker, context)
            try:
                if outcome == 'error': raise ValueError('Expected synthetic failure')
            except ValueError:
                pass
            finally:
                if outcome == 'late_finish':
                    manifest['status'] = 'cleaned'
                    save_manifest(path, manifest)
                    recover(docker, context)
                else:
                    cleanup(docker, manifest)
                    save_manifest(path, manifest)
            assert not output(docker, 'ps', '-aq', '--filter', 'id='+cid)
            print(outcome, 'PASSED', flush=True)
        for outcome in ('cancel', 'crash'):
            options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {}
            with subprocess.Popen([sys.executable, __file__, '--child', context], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **options) as process:
                resource = json.loads(process.stdout.readline())
                if outcome == 'crash': process.kill()
                else:
                    # This pipe requests KeyboardInterrupt without needing a Windows console.
                    # A force-kill is separately verified as crash/recovery below.
                    process.stdin.write('cancel\n')
                    process.stdin.flush()
                try:
                    process.communicate(timeout=45)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    recover(docker, context)
                    raise
            if outcome == 'crash': recover(docker, context)
            assert json.loads(Path(resource['path']).read_text())['status'] == 'cleaned'
            assert not output(docker, 'ps', '-aq', '--filter', 'id='+resource['id'])
            print(outcome, 'PASSED', flush=True)


if __name__ == '__main__':
    if len(sys.argv) > 1: child(sys.argv[2])
    else: main()
