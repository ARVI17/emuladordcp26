"""Memoria operativa de solo lectura; nunca consulta inventarios, sesiones ni .env."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'docs/PROJECT_STATE.json'
RENDER = 'docs/PROJECT_STATUS.md'
PROJECT = 'emuladordcp26'
APP_PATHS = ['backend/app', 'backend/alembic', 'backend/requirements.txt', 'backend/Dockerfile',
             'frontend/src', 'frontend/public', 'frontend/package.json', 'frontend/package-lock.json',
             'frontend/Dockerfile', 'docker-compose.yml', 'nginx']
SHA = re.compile(r'^[0-9a-f]{40}$')
LABELS = {'available': 'Disponible', 'partial': 'Parcial', 'pending': 'Pendiente',
          'passed': 'Contrastado', 'not_applicable': 'No aplica'}


def command(root, args):
    result = subprocess.run(args, cwd=root, capture_output=True, text=True, encoding='utf-8',
                            errors='replace', timeout=20, check=False)
    if result.returncode:
        # stderr can contain private paths/configuration; never include it in reports.
        raise ValueError('No se pudo completar una comprobación local')
    return result.stdout.strip()


def load_plan(root):
    plan = json.loads((root/PLAN).read_text(encoding='utf-8'))
    if plan.get('schema_version') != 1:
        raise ValueError('Versión de memoria no reconocida')
    for field in ('mission', 'next_action', 'reviewed_on', 'sprint'):
        if not isinstance(plan.get(field), str) or not plan[field].strip():
            raise ValueError('Falta campo de memoria: '+field)
    reviewed = date.fromisoformat(plan['reviewed_on'])
    if reviewed > datetime.now(timezone.utc).date():
        raise ValueError('La fecha de revisión está en el futuro')
    items = plan.get('items', [])
    ids = [item['id'] for item in items]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Los hitos deben tener identificadores únicos')
    for item in items:
        if not re.fullmatch(r'[A-Z]+-[0-9]+', item['id']):
            raise ValueError('Identificador de hito inválido')
        if item.get('implementation') not in ('available', 'partial', 'pending'):
            raise ValueError('Estado de implementación inválido')
        if item.get('real_validation') not in ('passed', 'pending', 'not_applicable'):
            raise ValueError('Estado de validación real inválido')
        for field in ('title', 'gap'):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError('Descripción vacía: '+item['id'])
        for field in ('acceptance', 'evidence'):
            if not isinstance(item.get(field), list) or not item[field] or not all(isinstance(v, str) and v.strip() for v in item[field]):
                raise ValueError('Faltan criterios/evidencia: '+item['id'])
        for relative in item['evidence']:
            path = (root/relative).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file() or relative.startswith(('state/', 'backups/')):
                raise ValueError('Evidencia versionada no encontrada: '+relative)
        if not isinstance(item.get('depends_on'), list) or any(dep not in ids for dep in item['depends_on']):
            raise ValueError('Dependencia desconocida: '+item['id'])
    graph = {item['id']: item['depends_on'] for item in items}
    def visit(key, active):
        if key in active:
            raise ValueError('Ciclo entre hitos')
        for dependency in graph[key]:
            visit(dependency, active | {key})
    for key in graph:
        visit(key, set())
    return plan


def render_plan(plan):
    rows = ['# Estado y rumbo del proyecto', '',
            '<!-- Generado por scripts/project_status.py --render-plan; editar PROJECT_STATE.json. -->', '',
            f"Revisión humana: **{plan['reviewed_on']}**. Sprint: {plan['sprint']}.", '',
            plan['mission'], '', f"**Siguiente paso:** {plan['next_action']}", '',
            'Disponible significa código existente; la validación con el club real se registra por separado. '
            'Estos estados no se convierten en completos por pasar pruebas sintéticas.', '',
            '| Hito | Implementación | Club real | Falta |', '| --- | --- | --- | --- |']
    for item in plan['items']:
        rows.append(f"| {item['id']} · {item['title']} | {LABELS[item['implementation']]} | {LABELS[item['real_validation']]} | {item['gap']} |")
    rows += ['', '## Criterios para cerrar cada hito', '']
    for item in plan['items']:
        rows += [f"### {item['id']} · {item['title']}", '',
                 'Dependencias: '+(', '.join(item['depends_on']) or 'ninguna')+'.', '']
        rows.extend('- '+criterion for criterion in item['acceptance'])
        rows += ['', 'Código/evidencia: '+', '.join(f'[{path}](../{path})' for path in item['evidence'])+'.', '']
    rows += ['## Continuar sin perder contexto', '',
             '- [Prompt maestro](MASTER_PROMPT.md): visión, decisiones y ejecución por sprints.',
             '- [Siguiente sesión](NEXT_SESSION.md): entrega actual y acción concreta.',
             '- [Auditoría del 16 de noviembre](AUDIT_20261116.md): hechos comprobados y límites.',
             '- `python scripts/project_status.py`: genera el informe privado actual en `state/continuity/latest.md`.',
             '- `python scripts/project_status.py --check`: comprueba estructura, dependencias, evidencias y sincronía de esta vista.', '',
             'El informe privado muestra la hora de observación, Git, Docker y los últimos informes de pruebas. '
             'No reemplaza esta revisión humana ni acredita datos EA. No existe un agente de fondo trabajando entre sesiones.', '']
    return '\n'.join(rows)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirección no permitida en diagnóstico local')


def public_json(url):
    # Only called with the validated loopback binding below. Ignore proxy environment.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(url, timeout=5) as response:
        body = response.read(65537)
        if len(body) > 65536:
            raise ValueError('Respuesta demasiado grande')
        return json.loads(body)


def build_fields(value):
    if not isinstance(value, dict) or not SHA.fullmatch(str(value.get('revision', ''))):
        raise ValueError('Procedencia no reconocida')
    return {key: value.get(key) for key in ('revision', 'source_dirty', 'environment', 'built_at', 'edition')}


def runtime(root):
    context = command(root, ['docker', 'context', 'show'])
    detail = json.loads(command(root, ['docker', 'context', 'inspect', context]))[0]
    if not detail['Endpoints']['docker']['Host'].startswith(('npipe://', 'unix://')):
        return {'status': 'unavailable', 'reason': 'Motor remoto excluido del diagnóstico'}
    docker = ['docker', '--context', context]
    ids = command(root, docker+['ps', '-aq', '--no-trunc', '--filter', 'label=com.docker.compose.project='+PROJECT]).split()
    if not ids:
        return {'status': 'absent', 'services': []}
    containers = json.loads(command(root, docker+['inspect', *ids]))
    result = {'status': 'observed', 'services': []}
    seen, nginx = set(), None
    for c in containers:
        labels = c['Config']['Labels']
        service = labels.get('com.docker.compose.service')
        if labels.get('com.docker.compose.project') != PROJECT or service in seen:
            raise ValueError('Identidad ambigua de los contenedores')
        seen.add(service)
        result['services'].append({'service': service, 'id': c['Id'], 'image': c['Image'],
                                  'state': c['State']['Status'], 'health': c['State'].get('Health', {}).get('Status', 'unknown')})
        if service == 'nginx':
            nginx = c
    bindings = (nginx or {}).get('HostConfig', {}).get('PortBindings', {}).get('80/tcp') or []
    if len(bindings) != 1 or bindings[0].get('HostIp') not in ('127.0.0.1', '::1'):
        result['http'] = 'not_checked_unsafe_binding'
        return result
    port = int(bindings[0]['HostPort'])
    if not 1024 <= port <= 65535:
        raise ValueError('Puerto local inválido')
    host = '[::1]' if bindings[0]['HostIp'] == '::1' else '127.0.0.1'
    result['url'] = f'http://{host}:{port}'
    for name, path in [('backend_build', '/api/build'), ('frontend_build', '/build.json'), ('health', '/health')]:
        try:
            value = public_json(result['url']+path)
            result[name] = {key: value.get(key) for key in ('status', 'database')} if name == 'health' else build_fields(value)
        except (OSError, ValueError, TypeError, AttributeError):
            result[name] = None
    front, back = result.get('frontend_build'), result.get('backend_build')
    result['builds_match'] = front == back if front and back else None
    result['http'] = 'healthy' if result.get('health', {}) and result['health'].get('status') == 'healthy' else 'unavailable'
    if back:
        # This is a source comparison, never evidence of a deployment or a test pass.
        try:
            command(root, ['git', 'cat-file', '-e', back['revision']+'^{commit}'])
        except (OSError, ValueError, subprocess.TimeoutExpired):
            result['app_source_matches_checkout'] = None
        else:
            diff = subprocess.run(['git', 'diff', '--quiet', back['revision'], '--', *APP_PATHS], cwd=root,
                                  capture_output=True, timeout=20, check=False)
            untracked = command(root, ['git', 'ls-files', '--others', '--exclude-standard', '--', *APP_PATHS])
            result['app_source_matches_checkout'] = (diff.returncode == 0 and not untracked) if diff.returncode in (0, 1) else None
    return result


def reports(root):
    rows, invalid = [], 0
    for path in (root/'state/sprints').glob('emuladordcp26-check-*/result.json'):
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(value, dict) or not SHA.fullmatch(str(value.get('git_sha', ''))):
                raise ValueError('Informe sin procedencia')
            steps = value.get('steps', [])
            row = {key: value.get(key) for key in ('git_sha', 'scope', 'selected_pytest', 'selected_browser', 'status',
                                                  'started_at', 'finished_at', 'main_stack_unchanged', 'volumes_unchanged')}
            row.update(path=path.relative_to(root).as_posix(), source_dirty=value.get('served_build', {}).get('source_dirty'),
                       recorded_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                       steps=[{'name': s['name'], 'exit': s['exit']} for s in steps])
            # A partial run or failed cleanup cannot be relabelled as a full pass.
            required = {'build', 'startup', 'migration-current', 'migration-check', 'cleanup'}
            required |= {'full': {'pytest', 'vitest', 'playwright', 'extension'}, 'backend': {'pytest'},
                         'frontend': {'vitest', 'playwright'}, 'extension': {'extension'}}.get(row['scope'], set())
            passed = {s['name'] for s in steps if s['exit'] == 0}
            row['verified_pass'] = bool(row['status'] == 'PASSED' and row['scope'] in ('full', 'backend', 'frontend', 'extension')
                                        and required <= passed and all(s['exit'] == 0 for s in steps)
                                        and row['main_stack_unchanged'] is True and row['volumes_unchanged'] is True)
            rows.append(row)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            invalid += 1
    rows.sort(key=lambda r: r['recorded_at'], reverse=True)
    return {'latest': rows[0] if rows else None,
            'latest_full_pass': next((r for r in rows if r['verified_pass'] and r['scope'] == 'full'
                                      and r['selected_pytest'] == 'all' and r['selected_browser'] == 'all'), None),
            'invalid_reports': invalid}


def reference_freshness(root):
    """Inspect public bundled metadata only; never renew evidence or fetch sources."""
    current = datetime.now(timezone.utc)
    result = []
    for relative in ('backend/app/data/fc27_references.json', 'backend/app/data/fc27_content.json', 'backend/app/data/fc27_variants.json'):
        row = {'path': relative, 'active': 0, 'expired': 0, 'pending': 0, 'status': 'observed'}
        try:
            value = json.loads((root/relative).read_text(encoding='utf-8'))
            if relative.endswith('fc27_variants.json'):
                # This catalog applies a single documentary review window to its items.
                items = [dict(observed_at=value.get('observed_at'), valid_until=value.get('valid_until'),
                              validation_status='documented') for _ in value['items']]
                row['pending'] = len(value.get('pending', {}))
            else:
                items = value if isinstance(value, list) else [value, *value.get('articles', [])]
            for item in items:
                until, observed = item.get('valid_until'), item.get('observed_at') or item.get('verified_at')
                if item.get('validation_status', item.get('status')) != 'documented' or not until or not observed:
                    row['pending'] += 1
                    continue
                end, start = datetime.fromisoformat(until), datetime.fromisoformat(observed)
                if end.tzinfo is None or start.tzinfo is None or start > current or end <= start:
                    row['pending'] += 1
                elif current >= end:
                    row['expired'] += 1
                else:
                    row['active'] += 1
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            row.update(status='unknown', active=None, expired=None, pending=None)
        result.append(row)
    return result


def snapshot(root, include_runtime=True):
    plan = load_plan(root)
    result = {'observed_at': datetime.now(timezone.utc).isoformat(), 'plan_reviewed_on': plan['reviewed_on'],
              'plan_age_days': (datetime.now(timezone.utc).date()-date.fromisoformat(plan['reviewed_on'])).days,
              'next_action': plan['next_action'], 'tests': reports(root), 'public_evidence': reference_freshness(root)}
    try:
        result['git'] = {'sha': command(root, ['git', 'rev-parse', 'HEAD']),
                         'branch': command(root, ['git', 'branch', '--show-current']),
                         'dirty': bool(command(root, ['git', 'status', '--porcelain']))}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        result['git'] = None
    try:
        result['runtime'] = runtime(root) if include_runtime else {'status': 'not_checked'}
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.TimeoutExpired):
        result['runtime'] = {'status': 'unavailable', 'reason': 'No se pudo acreditar Docker local'}
    return result


def render_snapshot(value):
    git, run = value['git'] or {}, value['runtime']
    lines = ['# Continuidad local — observación puntual', '', f"Observado: {value['observed_at']}.",
             f"Plan revisado: {value['plan_reviewed_on']} ({value['plan_age_days']} días).", '',
             f"Rama: {git.get('branch', 'desconocida')}. HEAD: {git.get('sha', 'desconocido')}. Cambios locales: {git.get('dirty', 'desconocido')}.", '',
             f"Docker: {run['status']}. URL: {run.get('url', 'no acreditada')}.",
             f"Builds iguales: {run.get('builds_match', 'desconocido')}. Código de aplicación igual al checkout: {run.get('app_source_matches_checkout', 'desconocido')}.", '']
    for service in run.get('services', []):
        lines.append(f"- {service['service']}: {service['state']} / {service['health']}.")
    for key in ('backend_build', 'frontend_build'):
        build = run.get(key) or {}
        lines += ['', f"{key}: {build.get('revision', 'no acreditado')}; árbol al construir: {build.get('source_dirty', 'desconocido')}."]
    lines += ['', '## Vigencia del contenido incluido en el checkout', '']
    for row in value['public_evidence']:
        lines.append(f"- {row['path']}: {row['active']} vigentes, {row['expired']} vencidos, {row['pending']} pendientes; {row['status']}.")
    lines += ['', 'Estas fechas no acreditan la exactitud del contenido. Una revisión vencida debe contrastarse con su fuente; '
              'el diagnóstico no la renueva. Las formaciones tienen además su propia guarda en squad_analysis.py.']
    for key, title in [('latest', 'Último informe local'), ('latest_full_pass', 'Último pase integral local')]:
        row = value['tests'][key]
        lines += ['', '## '+title, '']
        if not row:
            lines.append('Sin evidencia local suficiente.')
            continue
        lines += [f"{row['status']} · ámbito {row['scope']} · SHA {row['git_sha']} · cambios al construir {row['source_dirty']}.",
                  f"Pytest: {row['selected_pytest']}; navegador: {row['selected_browser']}.",
                  f"Pase con cierre y aislamiento acreditados: {row['verified_pass']}. Informe: {row['path']}.",
                  'Es evidencia de ese SHA y alcance; no acredita automáticamente el HEAD actual ni una sesión EA.']
    lines += ['', f"Informes ilegibles/incompletos: {value['tests']['invalid_reports']}.", '',
              '## Siguiente acción', '', value['next_action'], '',
              'Este diagnóstico no consulta cuentas, inventario, secretos, imágenes ni la base personal. '
              'No arranca, detiene, migra ni despliega servicios. Consulta NEXT_SESSION.md y PROJECT_STATUS.md para continuar.', '']
    return '\n'.join(lines)


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temp.write_text(text, encoding='utf-8')
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def write_status(root=ROOT, include_runtime=True):
    value = snapshot(root, include_runtime)
    target = root/'state/continuity'
    atomic_write(target/'latest.json', json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    atomic_write(target/'latest.md', render_snapshot(value))
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Valida la memoria versionada sin Docker ni red')
    mode.add_argument('--render-plan', action='store_true', help='Regenera PROJECT_STATUS.md desde PROJECT_STATE.json')
    parser.add_argument('--offline', action='store_true', help='Informe local sin consultar Docker/HTTP')
    args = parser.parse_args()
    plan = load_plan(ROOT)
    expected = render_plan(plan)
    if args.render_plan:
        atomic_write(ROOT/RENDER, expected)
    elif args.check:
        if not (ROOT/RENDER).is_file() or (ROOT/RENDER).read_text(encoding='utf-8') != expected:
            raise ValueError('Vista desactualizada: ejecuta python scripts/project_status.py --render-plan')
        print('Memoria, dependencias y evidencias: PASA. No acredita finalización del producto.')
    else:
        write_status(include_runtime=not args.offline)
        print('Informe actualizado: state/continuity/latest.md (observación puntual, no despliegue)')


if __name__ == '__main__':
    main()
