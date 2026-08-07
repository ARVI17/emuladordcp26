import re
import subprocess
import time
import unicodedata
from pathlib import Path
from app.core.config import settings

class AdbError(RuntimeError): pass

class AdbBridge:
    def __init__(self, executable: str | None = None):
        self.executable = executable or settings.adb_path

    def _run(self, args: list[str], timeout: float = 12, binary: bool = False):
        if not settings.adb_enabled: raise AdbError("El puente ADB está desactivado")
        try:
            result = subprocess.run([self.executable, *args], capture_output=True, timeout=timeout, check=False)
        except FileNotFoundError as exc: raise AdbError("ADB no está instalado en el contenedor") from exc
        except subprocess.TimeoutExpired as exc: raise AdbError("ADB no respondió a tiempo") from exc
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", "replace").strip() or result.stdout.decode("utf-8", "replace").strip()
            raise AdbError(detail[:300] or "Comando ADB rechazado")
        return result.stdout if binary else result.stdout.decode("utf-8", "replace").strip()

    def connect(self, address: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9._-]+:[0-9]{2,5}", address): raise AdbError("Dirección ADB inválida")
        if not 1 <= int(address.rsplit(":", 1)[1]) <= 65535: raise AdbError("Puerto ADB inválido")
        output = self._run(["connect", address], timeout=20)
        if any(term in output.lower() for term in ("unable", "failed", "cannot", "refused", "offline")): raise AdbError(output)
        return output

    def devices(self) -> list[dict]:
        output = self._run(["devices", "-l"])
        rows = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                rows.append({"serial": parts[0], "state": parts[1], "details": " ".join(parts[2:])})
        return rows

    def _device(self, serial: str, command: list[str], timeout: float = 12, binary: bool = False):
        if not re.fullmatch(r"[a-zA-Z0-9._:-]+", serial): raise AdbError("Identificador de dispositivo inválido")
        return self._run(["-s", serial, *command], timeout=timeout, binary=binary)

    def screenshot(self, serial: str) -> bytes:
        content = self._device(serial, ["exec-out", "screencap", "-p"], timeout=20, binary=True)
        if not content.startswith(b"\x89PNG"): raise AdbError("El dispositivo no devolvió una captura PNG")
        return content

    def screen_size(self, serial: str) -> tuple[int, int] | None:
        output = self._device(serial, ["shell", "wm", "size"])
        matches = re.findall(r"(\d+)x(\d+)", output)
        return (int(matches[-1][0]), int(matches[-1][1])) if matches else None

    def tap(self, serial: str, x: int, y: int):
        self._device(serial, ["shell", "input", "tap", str(x), str(y)])

    def swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int):
        self._device(serial, ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])

    def keyevent(self, serial: str, code: int):
        if code not in {4, 66, 67, 111, 123}: raise AdbError("Tecla no permitida")
        self._device(serial, ["shell", "input", "keyevent", str(code)])

    def input_text(self, serial: str, text: str):
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        safe = re.sub(r"[^a-zA-Z0-9 ._-]", "", normalized).strip()[:100].replace(" ", "%s")
        if not safe: raise AdbError("Texto vacío después de validarlo")
        self._device(serial, ["shell", "input", "text", safe])

def build_dcp_steps(calibration: dict, players: list[dict]) -> list[dict]:
    wait = int(calibration.get("wait_ms", 900))
    steps: list[dict] = []
    for index, player in enumerate(players, 1):
        steps.extend([
            {"action": "tap", "x": calibration["open_search_x"], "y": calibration["open_search_y"], "label": f"Abrir búsqueda {index}/{len(players)}"},
            {"action": "wait", "ms": wait, "label": "Esperar interfaz"},
            {"action": "tap", "x": calibration["search_field_x"], "y": calibration["search_field_y"], "label": "Activar buscador"},
            {"action": "text", "value": player["name"], "label": f"Buscar {player['name']}"},
            {"action": "wait", "ms": wait, "label": "Esperar resultados"},
            {"action": "tap", "x": calibration["first_result_x"], "y": calibration["first_result_y"], "label": f"Seleccionar resultado para {player['name']}"},
            {"action": "wait", "ms": wait, "label": "Verificar selección"},
            {"action": "tap", "x": calibration["add_player_x"], "y": calibration["add_player_y"], "label": f"Añadir {player['name']}"},
            {"action": "wait", "ms": wait, "label": "Esperar plantilla"},
        ])
    return steps

def run_step(bridge: AdbBridge, serial: str, step: dict):
    action = step.get("action")
    if action == "tap": bridge.tap(serial, int(step["x"]), int(step["y"]))
    elif action == "swipe": bridge.swipe(serial, int(step["x1"]), int(step["y1"]), int(step["x2"]), int(step["y2"]), int(step.get("duration_ms", 350)))
    elif action == "text": bridge.input_text(serial, str(step["value"]))
    elif action == "keyevent": bridge.keyevent(serial, int(step["code"]))
    elif action == "wait": time.sleep(min(5, max(0.1, int(step.get("ms", 500)) / 1000)))
    else: raise AdbError(f"Acción no permitida: {action}")
