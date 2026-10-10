import re
import subprocess
import time
import unicodedata
import xml.etree.ElementTree as ET
from uuid import uuid4
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

    def pair(self, address: str, pairing_code: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9._-]+:[0-9]{2,5}", address): raise AdbError("Dirección ADB inválida")
        if not 1 <= int(address.rsplit(":", 1)[1]) <= 65535: raise AdbError("Puerto ADB inválido")
        if not re.fullmatch(r"[0-9]{6}", pairing_code): raise AdbError("Código de emparejamiento inválido")
        try:
            output = self._run(["pair", address, pairing_code], timeout=25)
        except AdbError as exc:
            raise AdbError(str(exc).replace(pairing_code, "[redactado]")) from None
        sanitized = output.replace(pairing_code, "[redactado]")
        if any(term in sanitized.lower() for term in ("unable", "failed", "cannot", "refused", "incorrect")): raise AdbError(sanitized)
        return sanitized

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
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise AdbError("El dispositivo no devolvió una captura PNG")
        from app.services.import_export import validate_image
        try:
            validate_image(content)
        except ValueError as exc:
            raise AdbError("La captura PNG es inválida o excede los límites permitidos") from exc
        return content

    def ui_hierarchy(self, serial: str) -> bytes:
        """Read Android's accessibility tree without retaining it on either system."""
        path = f"/data/local/tmp/emuladordcp26-ui-{uuid4().hex}.xml"
        try:
            self._device(serial, ["shell", "uiautomator", "dump", path], timeout=20)
            content = self._device(serial, ["exec-out", "cat", path], timeout=10, binary=True)
        finally:
            try:
                self._device(serial, ["shell", "rm", "-f", path], timeout=5)
            except AdbError:
                pass
        if not content.startswith(b"<?xml") or len(content) > 2_000_000:
            raise AdbError("El dispositivo no devolvió una jerarquía de interfaz válida")
        return content

    def screen_size(self, serial: str) -> tuple[int, int] | None:
        output = self._device(serial, ["shell", "wm", "size"])
        matches = re.findall(r"(\d+)x(\d+)", output)
        return (int(matches[-1][0]), int(matches[-1][1])) if matches else None

    def tap(self, serial: str, x: int, y: int):
        if any(not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < 10000 for value in (x, y)):
            raise AdbError("Coordenadas no permitidas")
        self._device(serial, ["shell", "input", "tap", str(x), str(y)])

    def swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int):
        if any(not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < 10000 for value in (x1, y1, x2, y2)):
            raise AdbError("Coordenadas no permitidas")
        if not isinstance(duration_ms, int) or not 100 <= duration_ms <= 3000:
            raise AdbError("Duración de deslizamiento no permitida")
        self._device(serial, ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])

    def scroll_inventory_list_to_end(self, serial: str, width: int, height: int):
        if not 320 <= width <= 4320 or not 480 <= height <= 7680:
            raise AdbError("Resolución no permitida para desplazar el inventario")
        x, y1, y2 = width // 2, int(height * 0.8), int(height * 0.19)
        swipe = f"input swipe {x} {y1} {x} {y2} 120"
        self._device(serial, ["shell", "; ".join([swipe] * 5)], timeout=20)

    def keyevent(self, serial: str, code: int):
        if code not in {4, 66, 67, 111, 123}: raise AdbError("Tecla no permitida")
        self._device(serial, ["shell", "input", "keyevent", str(code)])

    def input_text(self, serial: str, text: str):
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        safe = re.sub(r"[^a-zA-Z0-9 ._-]", "", normalized).strip()[:100].replace(" ", "%s")
        if not safe: raise AdbError("Texto vacío después de validarlo")
        self._device(serial, ["shell", "input", "text", safe])

    def clear_search_text(self, serial: str):
        root = _ui_tree(self.ui_hierarchy(serial))
        fields = [node for node in root.iter("node") if node.attrib.get("class", "").endswith("EditText") and node.attrib.get("focused") == "true"]
        if len(fields) != 1:
            raise AdbError("No se pudo verificar el campo de búsqueda activo; continúa manualmente")
        existing = fields[0].attrib.get("text", "")
        if len(existing) > 500:
            raise AdbError("El contenido del buscador requiere revisión manual")
        if existing:
            self.keyevent(serial, 123)
            self._device(serial, ["shell", "input", "keyevent", *(["67"] * (len(existing) + 1))])
        checked = _ui_tree(self.ui_hierarchy(serial))
        current = [node for node in checked.iter("node") if node.attrib.get("class", "").endswith("EditText") and node.attrib.get("focused") == "true"]
        if len(current) != 1 or current[0].attrib.get("text", ""):
            raise AdbError("No se confirmó que el buscador quedó vacío; continúa manualmente")

    def select_verified_player(self, serial: str, player: dict, screen: tuple[int, int]):
        if self.screen_size(serial) != screen:
            raise AdbError("La resolución cambió durante la preparación")
        root = _ui_tree(self.ui_hierarchy(serial))
        matches = []
        for node in root.iter("node"):
            if node.attrib.get("class") != "android.widget.ListView":
                continue
            for row in list(node):
                if _matches_player(row, player, require_variant=True):
                    bounds = _visible_bounds(row, screen)
                    if bounds:
                        matches.append(bounds)
        if len(matches) != 1:
            raise AdbError("No se pudo identificar una única versión de la carta; revisa y selecciónala manualmente")
        x1, y1, x2, y2 = matches[0]
        self.tap(serial, (x1 + x2) // 2, (y1 + y2) // 2)

    def add_verified_player(self, serial: str, player: dict, screen: tuple[int, int]):
        if self.screen_size(serial) != screen:
            raise AdbError("La resolución cambió durante la preparación")
        root = _ui_tree(self.ui_hierarchy(serial))
        if any(node.attrib.get("class") == "android.widget.ListView" or node.attrib.get("class", "").endswith("EditText") for node in root.iter("node")):
            raise AdbError("La búsqueda sigue visible; abre y revisa el detalle de la carta antes de añadir")
        if not _matches_player(root, player, require_variant=True):
            raise AdbError("La pantalla no permite verificar la carta seleccionada; continúa manualmente")
        allowed = {"anadir", "agregar", "anadir jugador", "agregar jugador", "anadir a plantilla", "anadir a la plantilla", "agregar a la plantilla", "add", "add player", "add to squad"}
        buttons = [node for node in root.iter("node") if node.attrib.get("class") == "android.widget.Button" and node.attrib.get("clickable") == "true" and node.attrib.get("enabled") == "true" and _normalized(node.attrib.get("text", "")) in allowed]
        bounds = [_visible_bounds(node, screen) for node in buttons]
        bounds = [value for value in bounds if value]
        if len(bounds) != 1:
            raise AdbError("No se encontró un botón inequívoco para añadir la carta; continúa manualmente")
        x1, y1, x2, y2 = bounds[0]
        self.tap(serial, (x1 + x2) // 2, (y1 + y2) // 2)


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower().split())


def _ui_tree(content: bytes):
    if len(content) > 2_000_000 or b"<!DOCTYPE" in content.upper():
        raise AdbError("Jerarquía de interfaz no permitida")
    try:
        return ET.fromstring(content)
    except (ValueError, ET.ParseError) as exc:
        raise AdbError("No se pudo verificar la interfaz") from exc


def _matches_player(root, player: dict, *, require_variant: bool):
    values = {_normalized(node.attrib.get("text", "")) for node in root.iter("node") if not node.attrib.get("class", "").endswith("EditText") and node.attrib.get("visible-to-user") != "false"}
    expected = {_normalized(str(player.get(field, ""))) for field in ("name", "rating", "position")}
    if "" in expected or not expected.issubset(values):
        return False
    if require_variant:
        variant = _normalized(str(player.get("card_type", "")))
        if not variant or variant not in values:
            return False
        # A matching name and rating can still identify the wrong card version.
        # Require every known identifying field to be observable; unsupported
        # layouts/hidden card IDs deliberately leave selection to the user.
        for field in ("league", "club", "nationality", "card_id"):
            if player.get(field) and _normalized(str(player[field])) not in values:
                return False
        if "rare" in player and player.get("game_version", "FC26") == "FC26":
            rarity = {"raro", "rara", "rare", "oro raro", "oro rara", "rare gold"} if player["rare"] else {"comun", "common", "no raro", "no rara", "non rare", "oro comun", "common gold"}
            if not values.intersection(rarity):
                return False
        for field, labels in (("is_evolution", {"evolucion", "evolution", "evolucionada", "evolved"}), ("is_holographic", {"holografica", "holografico", "holographic"})):
            if player.get(field) and not values.intersection(labels):
                return False
        if player.get("game_version") == "FC27" and player.get("is_holographic") is False:
            normal = {"normal", "estandar", "standard", "no holografica", "no holografico", "non holographic"}
            if not values.intersection(normal):
                return False
    return True


def _visible_bounds(node, screen: tuple[int, int]):
    if node.attrib.get("visible-to-user") == "false":
        return None
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
    if not match:
        return None
    x1, y1, x2, y2 = (int(value) for value in match.groups())
    return (x1, y1, x2, y2) if 0 <= x1 < x2 <= screen[0] and 0 <= y1 < y2 <= screen[1] else None

def build_dcp_steps(calibration: dict, players: list[dict]) -> list[dict]:
    wait = int(calibration.get("wait_ms", 900))
    steps: list[dict] = []
    for index, player in enumerate(players, 1):
        steps.extend([
            {"action": "tap", "x": calibration["open_search_x"], "y": calibration["open_search_y"], "label": f"Abrir búsqueda {index}/{len(players)}"},
            {"action": "wait", "ms": wait, "label": "Esperar interfaz"},
            {"action": "tap", "x": calibration["search_field_x"], "y": calibration["search_field_y"], "label": "Activar buscador"},
            {"action": "clear_text", "label": "Vaciar y verificar buscador"},
            {"action": "text", "value": player["name"], "label": f"Buscar {player['name']}"},
            {"action": "wait", "ms": wait, "label": "Esperar resultados"},
            {"action": "select_verified", "player": dict(player), "screen": [calibration["screen_width"], calibration["screen_height"]], "label": f"Verificar y seleccionar versión de {player['name']}"},
            {"action": "wait", "ms": wait, "label": "Verificar selección"},
            {"action": "add_verified", "player": dict(player), "screen": [calibration["screen_width"], calibration["screen_height"]], "label": f"Verificar botón y añadir {player['name']}"},
            {"action": "wait", "ms": wait, "label": "Esperar plantilla"},
        ])
    return steps

def run_step(bridge: AdbBridge, serial: str, step: dict):
    action = step.get("action")
    if action == "tap": bridge.tap(serial, int(step["x"]), int(step["y"]))
    elif action == "swipe": bridge.swipe(serial, int(step["x1"]), int(step["y1"]), int(step["x2"]), int(step["y2"]), int(step.get("duration_ms", 350)))
    elif action == "text": bridge.input_text(serial, str(step["value"]))
    elif action == "clear_text": bridge.clear_search_text(serial)
    elif action == "select_verified": bridge.select_verified_player(serial, step["player"], tuple(step["screen"]))
    elif action == "add_verified": bridge.add_verified_player(serial, step["player"], tuple(step["screen"]))
    elif action == "keyevent": bridge.keyevent(serial, int(step["code"]))
    elif action == "wait": time.sleep(min(5, max(0.1, int(step.get("ms", 500)) / 1000)))
    else: raise AdbError(f"Acción no permitida: {action}")
