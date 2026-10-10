"""Regression tests for device ownership, cancellation and scan consistency.

All device I/O is simulated. No test connects to a real ADB device.
"""
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api import emulator
from app.db.session import SessionLocal
from app.models.entities import AutomationPlan, InventoryScan, Player
from app.services.adb import AdbBridge, AdbError
from app.services.import_export import parse_dcp_requirements, review_dcp_requirements
from test_emulator import CALIBRATION, feasible_solution


class FakeBridge:
    def devices(self):
        return [{"serial": "host.docker.internal:5555", "state": "device"}]

    def screen_size(self, serial):
        return (1080, 2400)

    def screenshot(self, serial):
        return b"fake-png-not-decoded-by-stub"


def prepared(client):
    segment_id, ids = feasible_solution(client)
    response = client.post("/emulator/plans", json={"segment_id": segment_id, "player_ids": ids})
    assert response.status_code == 201
    plan_id = response.json()["id"]
    assert client.put("/emulator/calibration", json=CALIBRATION).status_code == 200
    result = client.post(f"/emulator/plans/{plan_id}/prepare")
    assert result.status_code == 200
    return result.json(), ids


def candidate(name, rating=80):
    return {"name": name, "rating": rating, "position": "MC", "source_page": 1, "confidence": {}}


def reviewed(name, **extra):
    return {"name": name, "rating": 80, "position": "MC", "league": "Liga real", "club": "Club real", "nationality": "Colombia", **extra}


def capture_scan(client, monkeypatch, candidates):
    monkeypatch.setattr(emulator, "AdbBridge", FakeBridge)
    monkeypatch.setattr(emulator, "ocr_inventory", lambda *args: {"raw_text": "", "candidates": candidates})
    scan = client.post("/emulator/scans").json()
    response = client.post(f"/emulator/scans/{scan['id']}/capture")
    assert response.status_code == 200
    return response.json()["scan"]


def import_body(scan_id, candidate_id, name, **extra):
    return {"confirmation": f"IMPORTAR {scan_id}", "candidate_ids": [candidate_id], "players": [reviewed(name, **extra)]}


def test_two_plan_executions_cannot_reserve_same_device(client, monkeypatch):
    first, _ = prepared(client)
    second, _ = prepared(client)
    entered = threading.Event()
    release = threading.Event()

    class SlowBridge(FakeBridge):
        def devices(self):
            entered.set()
            assert release.wait(5)
            return super().devices()

    monkeypatch.setattr(emulator, "AdbBridge", SlowBridge)
    monkeypatch.setattr(emulator, "execute_automation_plan", lambda *args: None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        running = pool.submit(client.post, f"/emulator/plans/{first['id']}/execute", json={"confirmation": f"PREPARAR {first['id']}"})
        assert entered.wait(5)
        try:
            other = client.post(f"/emulator/plans/{second['id']}/execute", json={"confirmation": f"PREPARAR {second['id']}"})
            assert other.status_code == 409
        finally:
            release.set()
        assert running.result(timeout=5).status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AutomationPlan).where(AutomationPlan.status == "queued")) == 1


def test_manual_inputs_and_scan_advance_reject_reserved_device(client, monkeypatch):
    plan, _ = prepared(client)
    scan = capture_scan(client, monkeypatch, [candidate("Una carta")])
    with SessionLocal() as db:
        db.get(AutomationPlan, plan["id"]).status = "queued"
        db.commit()
    assert client.post("/emulator/tap", json={"x": 10, "y": 10}).status_code == 409
    assert client.post("/emulator/swipe", json={"x1": 10, "y1": 10, "x2": 20, "y2": 20}).status_code == 409
    assert client.post(f"/emulator/scans/{scan['id']}/advance").status_code == 409


def test_cancel_during_step_blocks_reprepare_until_worker_stops(client, monkeypatch):
    plan, _ = prepared(client)
    calls = []
    monkeypatch.setattr(emulator, "AdbBridge", FakeBridge)

    def cancel_in_flight(bridge, serial, step):
        calls.append(serial)
        with SessionLocal() as db:
            assert emulator.cancel_plan(plan["id"], db)["worker_active"] is True
            config = emulator.emulator_config(db)
            config["serial"] = "other-device"
            emulator.save_emulator_config(db, config)
            db.commit()
            with pytest.raises(HTTPException) as error:
                emulator.prepare_plan(plan["id"], db)
            assert error.value.status_code == 409

    monkeypatch.setattr(emulator, "run_step", cancel_in_flight)
    response = client.post(f"/emulator/plans/{plan['id']}/execute", json={"confirmation": f"PREPARAR {plan['id']}"})
    assert response.status_code == 200
    finished = next(row for row in client.get("/emulator/plans").json() if row["id"] == plan["id"])
    assert finished["status"] == "cancelled" and finished["worker_active"] is False
    assert calls == ["host.docker.internal:5555"]
    assert client.post(f"/emulator/plans/{plan['id']}/prepare").status_code == 200
    emulator.execute_automation_plan(plan["id"], generation=finished["execution_generation"] - 1)
    assert len(calls) == 1


def test_cancel_on_last_step_remains_cancelled(client, monkeypatch):
    plan, _ = prepared(client)
    with SessionLocal() as db:
        db.get(AutomationPlan, plan["id"]).steps = [{"action": "wait", "ms": 250, "label": "Último paso"}]
        db.commit()
    monkeypatch.setattr(emulator, "AdbBridge", FakeBridge)
    def last_step(*args):
        with SessionLocal() as db:
            emulator.cancel_plan(plan["id"], db)
    monkeypatch.setattr(emulator, "run_step", last_step)
    client.post(f"/emulator/plans/{plan['id']}/execute", json={"confirmation": f"PREPARAR {plan['id']}"})
    with SessionLocal() as db:
        row = db.get(AutomationPlan, plan["id"])
        assert row.status == "cancelled" and row.executed_at is None and row.worker_active is False


def test_player_changes_require_new_plan_review(client, monkeypatch):
    plan, ids = prepared(client)
    assert client.patch(f"/players/{ids[0]}", json={"name": "Nombre corregido"}).status_code == 200
    response = client.post(f"/emulator/plans/{plan['id']}/execute", json={"confirmation": f"PREPARAR {plan['id']}"})
    assert response.status_code == 409
    revised = client.post(f"/emulator/plans/{plan['id']}/prepare").json()
    assert "Nombre corregido" in [step["value"] for step in revised["steps"] if step["action"] == "text"]
    assert revised["approved_at"] is None


def test_recovery_marks_abandoned_work_without_running_commands(client, monkeypatch):
    plan, _ = prepared(client)
    with SessionLocal() as db:
        row = db.get(AutomationPlan, plan["id"])
        row.status = "running"
        row.worker_active = True
        generation = row.execution_generation
        db.commit()
    monkeypatch.setattr(emulator, "run_step", lambda *args: pytest.fail("Recovery must never execute a device command"))
    emulator.recover_interrupted_automation()
    with SessionLocal() as db:
        row = db.get(AutomationPlan, plan["id"])
        assert row.status == "failed" and not row.worker_active
        assert row.execution_generation > generation and "no se reanudaron" in row.last_error


def test_scan_candidate_ids_are_never_reused_after_partial_import(client, monkeypatch):
    scan = capture_scan(client, monkeypatch, [candidate("Primero"), candidate("Segundo")])
    path = f"/emulator/scans/{scan['id']}"
    assert client.post(path + "/import", json=import_body(scan["id"], 2, "Segundo")).status_code == 200
    monkeypatch.setattr(emulator, "ocr_inventory", lambda *args: {"raw_text": "", "candidates": [candidate("Tercero")]})
    captured = client.post(path + "/capture").json()["scan"]
    assert [(item["candidate_id"], item["name"]) for item in captured["candidates"]] == [(1, "Primero"), (3, "Tercero")]
    assert client.post(path + "/import", json=import_body(scan["id"], 2, "Segundo")).status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Player).where(Player.name == "Segundo")) == 1
        assert db.get(InventoryScan, scan["id"]).next_candidate_id == 4


def test_concurrent_scan_import_creates_exactly_one_player(client, monkeypatch):
    scan = capture_scan(client, monkeypatch, [candidate("Único concurrente")])
    start = threading.Barrier(2)
    def submit():
        start.wait(timeout=5)
        return client.post(f"/emulator/scans/{scan['id']}/import", json=import_body(scan["id"], 1, "Único concurrente"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [future.result(timeout=10) for future in [pool.submit(submit), pool.submit(submit)]]
    assert sorted(response.status_code for response in results) == [200, 409]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Player).where(Player.name == "Único concurrente")) == 1
        row = db.get(InventoryScan, scan["id"])
        assert row.imported_count == len(row.imported_player_ids) == 1


def test_continuation_preserves_last_page_hash_and_closed_scans_allow_new(client, monkeypatch):
    scan = capture_scan(client, monkeypatch, [candidate("Última página")])
    with SessionLocal() as db:
        db.get(InventoryScan, scan["id"]).captured_pages = 50
        db.commit()
    continued = client.post(f"/emulator/scans/{scan['id']}/continue")
    assert continued.status_code == 201
    next_id = continued.json()["id"]
    duplicate = client.post(f"/emulator/scans/{next_id}/capture").json()
    assert duplicate["duplicate_capture"] is True and duplicate["detected"] == 0
    assert client.post(f"/emulator/scans/{next_id}/cancel").json()["is_active"] is False
    assert client.post(f"/emulator/scans/{scan['id']}/cancel").status_code == 200
    new_scan = client.post("/emulator/scans").json()
    assert new_scan["id"] not in {scan["id"], next_id} and new_scan["is_active"] is True


def test_scan_rejects_wrong_edition_placeholders_and_missing_ocr_rating(client, monkeypatch):
    scan = capture_scan(client, monkeypatch, [candidate("Revisado")])
    path = f"/emulator/scans/{scan['id']}/import"
    other_edition = "FC26" if scan["game_version"] == "FC27" else "FC27"
    assert client.post(path, json=import_body(scan["id"], 1, "Revisado", game_version=other_edition)).status_code == 422
    assert client.post(path, json=import_body(scan["id"], 1, "Revisado", league="Por revisar")).status_code == 422
    monkeypatch.setattr(emulator, "ocr_inventory", lambda *args: {"raw_text": "", "candidates": [candidate("Sin media", None)]})
    capture = client.post(f"/emulator/scans/{scan['id']}/capture").json()
    assert capture["detected"] == 0
    assert [row["name"] for row in capture["scan"]["candidates"]] == ["Revisado"]


def test_ocr_comparators_are_preserved_and_unsupported_limits_are_flagged():
    requirements = parse_dcp_requirements("Ligas: Máx. 3\nClubes: Exactamente 2\nNacionalidades: Mín. 2")
    assert requirements["max_leagues"] == 3 and "min_leagues" not in requirements
    assert requirements["min_clubs"] == requirements["max_clubs"] == 2
    review = review_dcp_requirements("Raros: Máx. 2\nMedia: 84")
    assert not review["requirements"] and len(review["warnings"]) == 2
    assert review["requires_human_review"] is True
    both = parse_dcp_requirements("Ligas: Mín. 2\nLigas: Máx. 4")
    assert both["min_leagues"] == 2 and both["max_leagues"] == 4
    contradictory = review_dcp_requirements("Clubes: Mín. 4\nClubes: Máx. 2")
    assert not contradictory["requirements"] and "contradictorios" in contradictory["warnings"][0]


def test_pair_errors_redact_code_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr("app.services.adb.subprocess.run", lambda *args, **kwargs: subprocess.CompletedProcess(["adb"], 1, b"", b"pair failed for 123456"))
    with pytest.raises(AdbError) as error:
        AdbBridge().pair("localhost:37001", "123456")
    assert "123456" not in str(error.value)


def test_xml_cleanup_runs_after_dump_timeout_and_paths_are_unique(monkeypatch):
    bridge = AdbBridge()
    calls = []
    def device(serial, command, **kwargs):
        calls.append(command)
        if "uiautomator" in command:
            raise AdbError("timeout")
        return ""
    monkeypatch.setattr(bridge, "_device", device)
    for _ in range(2):
        with pytest.raises(AdbError):
            bridge.ui_hierarchy("emulator-5554")
    assert calls[1] == ["shell", "rm", "-f", calls[0][-1]]
    assert calls[3] == ["shell", "rm", "-f", calls[2][-1]]
    assert calls[0][-1] != calls[2][-1]


def test_screenshot_rejects_oversized_png_before_ocr(monkeypatch):
    bridge = AdbBridge()
    monkeypatch.setattr(bridge, "_device", lambda *args, **kwargs: b"\x89PNG\r\n\x1a\n" + b"x" * (10 * 1024 * 1024))
    with pytest.raises(AdbError):
        bridge.screenshot("emulator-5554")


def test_card_selection_requires_visible_unique_variant_and_never_taps_submit(monkeypatch):
    bridge = AdbBridge()
    card = {"name": "Carta exacta", "rating": 84, "position": "MC", "card_type": "Oro"}
    row = '<node bounds="[10,100][500,300]"><node text="Carta exacta"/><node text="84"/><node text="MC"/><node text="Oro"/></node>'
    tree = lambda rows: f'<?xml version="1.0"?><hierarchy><node class="android.widget.ListView">{rows}</node></hierarchy>'.encode()
    taps = []
    monkeypatch.setattr(bridge, "screen_size", lambda serial: (1080, 2400))
    monkeypatch.setattr(bridge, "tap", lambda serial, x, y: taps.append((x, y)))
    monkeypatch.setattr(bridge, "ui_hierarchy", lambda serial: tree(row))
    bridge.select_verified_player("emulator-5554", card, (1080, 2400))
    assert taps == [(255, 200)]
    monkeypatch.setattr(bridge, "ui_hierarchy", lambda serial: tree(row + row))
    with pytest.raises(AdbError):
        bridge.select_verified_player("emulator-5554", card, (1080, 2400))
    submit = '<node text="Entregar" class="android.widget.Button" clickable="true" enabled="true" bounds="[800,2000][1080,2300]"/>'
    monkeypatch.setattr(bridge, "ui_hierarchy", lambda serial: tree(row + submit))
    with pytest.raises(AdbError):
        bridge.add_verified_player("emulator-5554", card, (1080, 2400))
    add = submit.replace("Entregar", "Añadir")
    monkeypatch.setattr(bridge, "ui_hierarchy", lambda serial: tree(row + add))
    with pytest.raises(AdbError, match="búsqueda"):
        bridge.add_verified_player("emulator-5554", card, (1080, 2400))
    assert len(taps) == 1


def test_card_verification_requires_known_rarity_and_detail_fields(monkeypatch):
    bridge = AdbBridge()
    card = {"name": "Carta exacta", "rating": 84, "position": "MC", "card_type": "Oro", "rare": True, "club": "Club A"}
    values = '<node text="Carta exacta"/><node text="84"/><node text="MC"/><node text="Oro"/>'
    button = '<node text="Añadir" class="android.widget.Button" clickable="true" enabled="true" bounds="[800,2000][1080,2300]"/>'
    xml = lambda text: f'<?xml version="1.0"?><hierarchy><node>{text}{button}</node></hierarchy>'.encode()
    taps = []
    monkeypatch.setattr(bridge, "screen_size", lambda serial: (1080, 2400))
    monkeypatch.setattr(bridge, "tap", lambda *args: taps.append(args))
    monkeypatch.setattr(bridge, "ui_hierarchy", lambda serial: xml(values))
    with pytest.raises(AdbError):
        bridge.add_verified_player("emulator-5554", card, (1080, 2400))
    monkeypatch.setattr(bridge, "ui_hierarchy", lambda serial: xml(values + '<node text="Raro"/><node text="Club A"/>'))
    bridge.add_verified_player("emulator-5554", card, (1080, 2400))
    assert len(taps) == 1
