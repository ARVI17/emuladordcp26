import csv
import io
import re
import unicodedata
import xml.etree.ElementTree as ET
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import Player

FIELDS = ["name", "rating", "position", "league", "club", "nationality", "card_type", "rare", "special", "tradable", "price", "chemistry", "protected", "duplicate_untradeable"]
REQUIRED = {"name", "rating", "position", "league", "club", "nationality"}

def export_players(db: Session, excel: bool = False) -> tuple[bytes, str]:
    rows = [{field: getattr(player, field) for field in FIELDS} for player in db.scalars(select(Player).where(Player.deleted.is_(False))).all()]
    if excel:
        import pandas as pd

        output = io.BytesIO()
        frame = pd.DataFrame(rows, columns=FIELDS)
        frame.to_excel(output, index=False, engine="openpyxl")
        return output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + output.getvalue()).encode("utf-8"), "text/csv; charset=utf-8"

def parse_import(content: bytes, filename: str) -> list[dict]:
    if filename.lower().endswith(".xlsx"):
        import pandas as pd

        frame = pd.read_excel(io.BytesIO(content), engine="openpyxl")
        frame.columns = [str(c).strip().lower() for c in frame.columns]
        columns = set(frame.columns)
        raw_records = frame.fillna("").to_dict(orient="records")
    else:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        if not reader.fieldnames:
            raise ValueError("Archivo CSV vacío")
        normalized = {column: str(column).strip().lower() for column in reader.fieldnames if column is not None}
        columns = set(normalized.values())
        raw_records = [
            {normalized[key]: value for key, value in raw.items() if key in normalized}
            for raw in reader
        ]
    missing = REQUIRED - columns
    if missing: raise ValueError("Faltan columnas: " + ", ".join(sorted(missing)))
    records = []
    for raw in raw_records:
        record = {key: "" if raw.get(key) is None else raw.get(key, "") for key in FIELDS}
        record["name"] = str(record["name"]).strip()[:100]
        for field in ("position", "league", "club", "nationality", "card_type"): record[field] = str(record[field]).strip()
        record["rating"] = int(record["rating"]); record["price"] = int(record["price"] or 0); record["chemistry"] = int(record["chemistry"] or 0)
        for field in ("rare", "special", "tradable", "protected", "duplicate_untradeable"):
            record[field] = str(record[field]).strip().lower() in {"1", "true", "sí", "si", "yes"}
        if not 1 <= record["rating"] <= 99: raise ValueError(f"Media inválida para {record['name']}")
        records.append(record)
    return records

def ocr_image(content: bytes) -> dict:
    import cv2
    import numpy as np
    import pytesseract
    from PIL import Image

    array = np.frombuffer(content, np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None: raise ValueError("Imagen no válida")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
    processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    text = pytesseract.image_to_string(Image.fromarray(processed), lang="spa+eng")
    ratings = [int(value) for value in re.findall(r"\b([4-9][0-9])\b", text) if 40 <= int(value) <= 99]
    positions = re.findall(r"\b(POR|LD|DFC|LI|MCD|MC|MCO|ED|EI|DC)\b", text.upper())
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 2]
    return {"raw_text": text[:5000], "candidates": [{"name": lines[0] if lines else "", "rating": ratings[0] if ratings else None, "position": positions[0] if positions else "", "confidence": {"name": 0.45 if lines else 0.0, "rating": 0.7 if ratings else 0.0, "position": 0.75 if positions else 0.0}}], "requires_confirmation": True}

OCR_UI_WORDS = {
    "club", "plantilla", "buscar", "filtros", "ordenar", "calidad", "posicion", "liga",
    "nacionalidad", "precio", "quimica", "transferible", "intransferible", "volver", "menu",
}
PLAYER_POSITIONS = {"POR", "LD", "DFC", "LI", "MCD", "MC", "MCO", "MD", "MI", "ED", "EI", "SD", "DC"}
PLAYER_STAT = re.compile(r"^(?:SAL|PAR|SAQ|REF|VEL|POS|RIT|TIR|PAS|REG|DEF|F[IÍ]S)\s*\d{1,3}$", re.IGNORECASE)

def _plain(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()

def _candidate(name: str, rating: int, position: str, page: int, confidence: float) -> dict:
    return {
        "name": name[:100], "rating": rating, "position": position, "source_page": page,
        "confidence": {"name": confidence, "rating": confidence, "position": confidence},
    }

def extract_accessibility_inventory_candidates(content: bytes | str, page: int = 1) -> list[dict]:
    """Extract Companion player rows from a bounded, temporary UIAutomator tree."""
    if isinstance(content, bytes):
        if len(content) > 2_000_000: return []
        content = content.decode("utf-8", "replace")
    try:
        root = ET.fromstring(content)
    except (ET.ParseError, ValueError):
        return []
    screen_text = [node.attrib.get("text", "").strip() for node in root.iter("node")]
    if not any(_plain(value) == "futb. de mi club" for value in screen_text):
        return []
    candidates: list[dict] = []
    for list_view in root.iter("node"):
        if list_view.attrib.get("class") != "android.widget.ListView": continue
        for row in list(list_view):
            values = [node.attrib.get("text", "").strip() for node in row.iter("node") if node.attrib.get("text", "").strip()]
            rating_index = next((index for index, value in enumerate(values) if value.isdigit() and 40 <= int(value) <= 99), None)
            if rating_index is None: continue
            position_index = next((index for index in range(rating_index + 1, len(values)) if values[index].upper() in PLAYER_POSITIONS), None)
            if position_index is None: continue
            name = ""
            for value in values[position_index + 1:]:
                plain = _plain(value)
                if not plain or value.isdigit() or value.upper() in PLAYER_POSITIONS or PLAYER_STAT.fullmatch(value): continue
                if any(word == plain or plain.startswith(f"{word} ") for word in OCR_UI_WORDS): continue
                if re.search(r"[A-Za-zÀ-ÿ]", value):
                    name = value.strip(" -|:")
                    break
            if name:
                candidates.append(_candidate(name, int(values[rating_index]), values[position_index].upper(), page, 0.99))
            if len(candidates) >= 30: return candidates
        if candidates: break
    return candidates

def find_accessibility_inventory_action(content: bytes | str, label: str) -> tuple[int, int, int, int] | None:
    if isinstance(content, bytes):
        if len(content) > 2_000_000: return None
        content = content.decode("utf-8", "replace")
    try:
        root = ET.fromstring(content)
    except (ET.ParseError, ValueError):
        return None
    if not any(_plain(node.attrib.get("text", "").strip()) == "futb. de mi club" for node in root.iter("node")):
        return None
    expected = _plain(label)
    for node in root.iter("node"):
        text = _plain(node.attrib.get("text", "").strip())
        if expected not in text or node.attrib.get("class") != "android.widget.Button": continue
        if node.attrib.get("clickable") != "true" or node.attrib.get("enabled") != "true": continue
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
        if match: return tuple(int(value) for value in match.groups())
    return None

def extract_inventory_candidates(text: str, page: int = 1) -> list[dict]:
    lines = [re.sub(r"\s+", " ", line).strip(" -|:") for line in text.splitlines() if len(line.strip()) > 1]
    candidates: list[dict] = []
    inline = re.compile(r"^(?P<rating>[4-9][0-9])\s+(?P<position>POR|LD|DFC|LI|MCD|MC|MCO|MD|MI|ED|EI|SD|DC)\s+(?P<name>.+)$", re.IGNORECASE)
    index = 0
    while index < len(lines) and len(candidates) < 30:
        match = inline.fullmatch(lines[index])
        if match:
            name = match.group("name").strip()
            if re.search(r"[A-Za-zÀ-ÿ]", name):
                candidates.append(_candidate(name, int(match.group("rating")), match.group("position").upper(), page, 0.72))
            index += 1
            continue
        if index + 2 < len(lines) and re.fullmatch(r"[4-9][0-9]", lines[index]) and lines[index + 1].upper() in PLAYER_POSITIONS:
            name = lines[index + 2].strip()
            plain = _plain(name)
            if re.search(r"[A-Za-zÀ-ÿ]", name) and not PLAYER_STAT.fullmatch(name) and not any(word == plain or plain.startswith(f"{word} ") for word in OCR_UI_WORDS):
                candidates.append(_candidate(name, int(lines[index]), lines[index + 1].upper(), page, 0.72))
                index += 3
                continue
        index += 1
    return candidates

def ocr_inventory(content: bytes, page: int = 1, hierarchy: bytes | str | None = None) -> dict:
    structured = extract_accessibility_inventory_candidates(hierarchy, page) if hierarchy else []
    if structured:
        summary = "\n".join(f"{item['rating']} {item['position']} {item['name']}" for item in structured)
        return {"raw_text": summary, "candidates": structured, "mode": "inventory_review", "requires_confirmation": True, "extraction_source": "accessibility", "ocr_used": False}
    result = ocr_image(content)
    result["candidates"] = extract_inventory_candidates(result["raw_text"], page)
    result["mode"] = "inventory_review"
    result["extraction_source"] = "ocr"
    result["ocr_used"] = True
    return result

def parse_dcp_requirements(text: str) -> dict:
    plain = _plain(text)
    requirements: dict[str, int] = {}
    patterns = {
        "squad_size": r"(?:numero de jugadores|jugadores en la plantilla|tamano de plantilla).{0,35}?(\d{1,2})",
        "min_rating": r"(?:valoracion|media).{0,35}?(\d{2})",
        "min_chemistry": r"quimica.{0,35}?(\d{1,2})",
        "min_rare": r"(?:jugadores raros|raros).{0,35}?(\d{1,2})",
        "min_special": r"(?:jugadores especiales|especiales).{0,35}?(\d{1,2})",
        "min_leagues": r"(?:ligas|campeonatos).{0,35}?(\d{1,2})",
        "min_clubs": r"clubes.{0,35}?(\d{1,2})",
        "min_nations": r"(?:paises|naciones|nacionalidades).{0,35}?(\d{1,2})",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, plain, re.DOTALL)
        if match: requirements[key] = int(match.group(1))
    if "squad_size" not in requirements and requirements: requirements["squad_size"] = 11
    return requirements
