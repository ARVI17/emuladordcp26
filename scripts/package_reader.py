"""Package the exact compiled extension from a successful isolated Docker run."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True, encoding='utf-8').strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', help='state/sprints/<project>/result.json')
    args = parser.parse_args()
    report_path = Path(args.report).resolve()
    if not report_path.is_relative_to((ROOT/'state/sprints').resolve()):
        raise ValueError('El informe debe pertenecer a las pruebas locales de este repositorio')
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if report['status'] != 'PASSED' or report['scope'] not in {'full','extension'}:
        raise ValueError('Se requiere una prueba pasada de la extensión compilada')
    config = json.loads((report_path.parent/'compose.json').read_text(encoding='utf-8'))
    image = config['services']['extension-test']['image']
    if not image.startswith(report['project']+':'):
        raise ValueError('Imagen ajena al proyecto de verificación')
    image_id = docker('image','inspect','--format','{{.Id}}',image)
    folder = ROOT/'state'/('reader-package-'+uuid.uuid4().hex[:10])
    folder.mkdir()
    marker = uuid.uuid4().hex
    container = docker('create','--label','io.fc27.package='+marker,image_id)
    try:
        docker('cp',container+':/app/.output/chrome-mv3',str(folder))
    finally:
        owned = json.loads(docker('inspect',container))[0]
        if owned['Config']['Labels'].get('io.fc27.package') != marker or owned['State']['Running'] or owned['Mounts']:
            raise RuntimeError('No se puede retirar el contenedor de empaquetado: identidad inesperada')
        docker('rm',container)
    build = folder/'chrome-mv3'
    manifest = json.loads((build/'manifest.json').read_text(encoding='utf-8'))
    destination = folder/f'club-lab-reader-{manifest["version"]}.zip'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(build.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(build).as_posix(), (2026,1,1,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info,path.read_bytes())
    metadata = dict(version=manifest['version'],sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
        git_sha=report['git_sha'],source_dirty=report['served_build']['source_dirty'],
        image_id=image_id,report=str(report_path),zip=str(destination),unpacked=str(build))
    (folder/'package.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps(metadata,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
