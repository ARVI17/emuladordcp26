"""Capturas sintéticas, sin sesión ni datos EA; API y OCR real por tuberías."""
import io
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models.assisted import CaptureSession, VisualReading, VisualSnapshot
from app.models.entities import Player, now
from app.services.scan_ocr import recognize, ScanCancelled
from test_assisted import enter

pytestmark = pytest.mark.catalog_boundary


def start(client):
    r = client.post('/visual-scans', json={'consent': True})
    assert r.status_code == 201, r.text
    return r.json()['id']


def pixels(sequence=1):
    output = io.BytesIO()
    Image.new('RGB', (160, 160), (sequence % 255, 220, 200)).save(output, format='PNG')
    return output.getvalue()


def frame(client, monkeypatch, identifier, sequence, text):
    with SessionLocal() as db:
        row = db.get(CaptureSession, identifier)
        row.scan_data = {**row.scan_data, 'last_frame_at': (now()-timedelta(seconds=2)).isoformat()}
        db.commit()
    monkeypatch.setattr('app.api.visual_scan.recognize', lambda content, cancelled: dict(text=text, lines={s: .96 for s in text.splitlines()}, seconds=.1))
    r = client.post(f'/visual-scans/{identifier}/frames?sequence={sequence}', content=pixels(sequence), headers={'Content-Type':'image/png'})
    assert r.status_code == 200, r.text
    return r.json()


def list_cards(client, identifier):
    return client.get(f'/visual-scans/{identifier}/candidates').json()['items']


def body(cards):
    return dict(phrase='GUARDAR SINCRONIZACION', edition='FC27', cards=[dict(
        candidate_key=c['candidate_key'],ordinal=c['ordinal'],name=c['name'],rating=c['rating'],
        position=c['position'],card_type='Oro común',is_loan=False,is_evolution=False) for c in cards])


def commit(client, identifier, payload):
    r = client.post(f'/visual-scans/{identifier}/transition', json={'action': 'stop'})
    assert r.status_code == 200, r.text
    r = client.post(f'/visual-scans/{identifier}/commit', json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_overlap_snapshot_idempotency_partial_and_seed_isolation(client, monkeypatch):
    enter(client)
    scan = start(client)
    names = [f'Futbolista {chr(65+i)}' for i in range(12)]
    for seq, group in enumerate((names[:8], names[4:]), 1):
        result = frame(client, monkeypatch, scan, seq, 'FC27 Mi club\n'+'\n'.join('84 MC '+name for name in group))
    assert result['pages'] == 2 and result['unique_candidates'] == 12
    assert not result['complete'] and result['coverage'] == 'unknown'
    assert client.get('/players').json()['items'] == []  # OCR nunca admite propiedad.
    payload = body(list_cards(client, scan))
    first = commit(client, scan, payload)
    second = client.post(f'/visual-scans/{scan}/commit', json=payload)
    assert second.status_code == 200 and second.json() == first
    assert len(first['changes']['added']) == 12
    assert client.get('/players').json()['total'] == 12
    partial = start(client)
    frame(client, monkeypatch, partial, 1, 'FC27 Mi club\n84 MC Futbolista A')
    cards = list_cards(client, partial)
    payload = body(cards)
    payload['cards'][0]['existing_player_id'] = cards[0]['existing'][0]['id']
    updated = commit(client, partial, payload)
    assert updated['previous_id'] == first['id'] and len(updated['changes']['preserved_unseen']) == 11
    assert updated['changes']['removed'] == [] and not updated['changes']['added']
    assert client.get('/players').json()['total'] == 12
    with SessionLocal() as db:
        assert db.scalar(select(func.count(VisualSnapshot.id))) == 2
        assert db.scalar(select(func.count(Player.id)).where(Player.club_context_id == 1)) == 132


def test_same_frame_copies_variants_remain_reviewable(client, monkeypatch):
    enter(client)
    scan = start(client)
    frame(client, monkeypatch, scan, 1, 'FC27 Mi club\n84 MC Carta Igual\n84 MC Carta Igual')
    cards = list_cards(client, scan)
    assert len(cards) == 2 and {c['copy_index'] for c in cards} == {1, 2}
    payload = body(cards)
    payload['cards'][1].update(card_type='TOTW', special=True, is_holographic=True)
    result = commit(client, scan, payload)
    assert len(result['changes']['added']) == 2
    rows = client.get('/players?availability=review_required').json()['items']
    assert len(rows) == 2  # A variant label alone does not prove distinct ownership.
    assert {r['card_type'] for r in rows} == {'Oro común', 'TOTW'}


@pytest.mark.parametrize('text', ['FC27 Mi club\nIniciar sesión\nContraseña secreta',
    'FC27 Mi club\nMFA 123456', 'FC27 Mi perfil\nCorreo electronico usuario@example.com',
    'FC27 Mi club\nPayment credit card 4111111111111111', 'Ventana desconocida'])
def test_sensitive_frames_pause_without_any_observation(client, monkeypatch, text):
    enter(client)
    scan = start(client)
    result = frame(client, monkeypatch, scan, 1, text)
    assert result['status'] == 'paused_sensitive'
    assert 'secreta' not in str(result) and '123456' not in str(result)
    assert list_cards(client, scan) == []
    with SessionLocal() as db:
        assert db.scalar(select(func.count(VisualReading.id))) == 0
    assert client.post(f'/visual-scans/{scan}/transition', json={'action':'resume'}).status_code == 409


def test_replay_rate_stopped_and_context_isolation(client, monkeypatch):
    enter(client)
    assert client.post('/visual-scans', json={'consent':False}).status_code == 422
    scan = start(client)
    frame(client, monkeypatch, scan, 1, 'FC27 Mi club\n84 MC Carta Uno')
    send=lambda seq: client.post(f'/visual-scans/{scan}/frames?sequence={seq}', content=pixels(2), headers={'Content-Type':'image/png'})
    assert send(1).status_code == 409
    assert send(2).status_code == 429
    client.post(f'/visual-scans/{scan}/transition', json={'action':'stop'})
    assert send(2).status_code == 409
    enter(client, 'Otro club aislado')
    assert client.get(f'/visual-scans/{scan}').status_code == 404
    assert client.get(f'/visual-scans/{scan}/candidates').status_code == 404


def test_cancel_during_ocr_discards_result_without_waiting_for_recognition(client, monkeypatch):
    enter(client)
    scan = start(client)
    began, stopped = threading.Event(), threading.Event()
    def slow(content, cancelled):
        began.set()
        assert stopped.wait(5)
        if cancelled():
            raise ScanCancelled()
        raise AssertionError('La cancelación no llegó al OCR')
    monkeypatch.setattr('app.api.visual_scan.recognize', slow)
    with ThreadPoolExecutor(2) as pool:
        task = pool.submit(lambda: client.post(f'/visual-scans/{scan}/frames?sequence=1', content=pixels(), headers={'Content-Type':'image/png'}))
        assert began.wait(5)
        response = client.post(f'/visual-scans/{scan}/transition', json={'action':'stop'})
        assert response.status_code == 200
        stopped.set()
        assert task.result().json() == {'discarded':True, 'stopped':True}
    assert not list_cards(client, scan)


def test_retired_identity_cannot_be_resurrected_and_commit_rolls_back(client, monkeypatch):
    enter(client)
    scan = start(client)
    frame(client, monkeypatch, scan, 1, 'FC27 Mi club\n84 MC Carta Retirada')
    result = commit(client, scan, body(list_cards(client, scan)))
    with SessionLocal() as db:
        db.get(Player, result['changes']['added'][0]).deleted = True
        db.commit()
    other = start(client)
    frame(client, monkeypatch, other, 1, 'FC27 Mi club\n84 MC Carta Nueva\n84 MC Carta Retirada')
    client.post(f'/visual-scans/{other}/transition', json={'action':'stop'})
    response = client.post(f'/visual-scans/{other}/commit', json=body(list_cards(client, other)))
    assert response.status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(func.count(VisualSnapshot.id))) == 1
        assert not db.scalar(select(Player.id).where(Player.name == 'Carta Nueva'))


def test_real_tesseract_multiple_cards_and_confidence_without_temp_images():
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30)
    img = Image.new('RGB', (1000, 580), 'white')
    draw = ImageDraw.Draw(img)
    names = ['Carta Alfa', 'Carta Bravo', 'Carta Charlie', 'Carta Delta', 'Carta Eco', 'Carta Foxtrot', 'Carta Golf', 'Carta Hotel']
    lines = ['FC27 Mi club']+[f'84 MC {name}' for name in names]
    for i, line in enumerate(lines):
        draw.text((25, 20+i*55), line, fill='black', font=font)
    output = io.BytesIO()
    img.save(output, format='PNG')
    result = recognize(output.getvalue())
    from app.services.assisted import parse_screen
    cards = parse_screen(result['text'], 'inventory')['cards']
    assert len(cards) == 8
    assert all(c['rating'] == 84 and c['position'] == 'MC' for c in cards)
    assert [c['name'] for c in cards] == names
    assert all(0 <= score <= 1 for score in result['lines'].values())
    assert result['seconds'] < 10


def test_cancellation_kills_running_tesseract(monkeypatch):
    import subprocess
    class Process:
        returncode = None
        killed = False
        def communicate(self, input=None, timeout=None):
            if self.killed:
                return b'', None
            raise subprocess.TimeoutExpired('tesseract', .25)
        def poll(self):
            return self.returncode
        def kill(self):
            self.killed = True
            self.returncode = -9
    process = Process()
    monkeypatch.setattr('app.services.scan_ocr.subprocess.Popen', lambda *a, **k: process)
    checks = 0
    def cancelled():
        nonlocal checks
        checks += 1
        return checks >= 3
    with pytest.raises(ScanCancelled):
        recognize(pixels(), cancelled)
    assert process.killed


def test_binary_limits_roi_validation_and_resolution_change(client, monkeypatch):
    enter(client)
    assert client.post('/visual-scans', json={'consent':True,'region':[90,0,20,100]}).status_code == 422
    scan = start(client)
    assert client.post(f'/visual-scans/{scan}/frames?sequence=1', content=b'a'*(4*1024*1024+1), headers={'Content-Type':'image/png'}).status_code == 413
    assert client.post(f'/visual-scans/{scan}/frames?sequence=1', content=b'not-image', headers={'Content-Type':'image/png'}).status_code == 422
    frame(client, monkeypatch, scan, 1, 'FC27 Mi club\n84 MC Carta Uno')
    output = io.BytesIO()
    Image.new('RGB',(320,160),'white').save(output,format='PNG')
    response = client.post(f'/visual-scans/{scan}/frames?sequence=2', content=output.getvalue(), headers={'Content-Type':'image/png'})
    assert response.status_code == 200 and response.json()['status'] == 'needs_review'
    assert response.json()['pages'] == 1
