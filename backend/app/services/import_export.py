import csv
import io
import re
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
import pytesseract
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import Player

FIELDS = ["name", "rating", "position", "league", "club", "nationality", "card_type", "rare", "special", "tradable", "price", "chemistry", "protected", "duplicate_untradeable"]
REQUIRED = {"name", "rating", "position", "league", "club", "nationality"}

def export_players(db: Session, excel: bool = False) -> tuple[bytes, str]:
    rows = [{field: getattr(player, field) for field in FIELDS} for player in db.scalars(select(Player).where(Player.deleted.is_(False))).all()]
    frame = pd.DataFrame(rows, columns=FIELDS)
    output = io.BytesIO()
    if excel:
        frame.to_excel(output, index=False, engine="openpyxl")
        return output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    output.write(frame.to_csv(index=False).encode("utf-8-sig"))
    return output.getvalue(), "text/csv; charset=utf-8"

def parse_import(content: bytes, filename: str) -> list[dict]:
    if filename.lower().endswith(".xlsx"):
        frame = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    else:
        frame = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    missing = REQUIRED - set(frame.columns)
    if missing: raise ValueError("Faltan columnas: " + ", ".join(sorted(missing)))
    records = []
    for raw in frame.fillna("").to_dict(orient="records"):
        record = {key: raw.get(key, "") for key in FIELDS}
        record["name"] = str(record["name"]).strip()[:100]
        for field in ("position", "league", "club", "nationality", "card_type"): record[field] = str(record[field]).strip()
        record["rating"] = int(record["rating"]); record["price"] = int(record["price"] or 0); record["chemistry"] = int(record["chemistry"] or 0)
        for field in ("rare", "special", "tradable", "protected", "duplicate_untradeable"):
            record[field] = str(record[field]).lower() in {"1", "true", "sí", "si", "yes"}
        if not 1 <= record["rating"] <= 99: raise ValueError(f"Media inválida para {record['name']}")
        records.append(record)
    return records

def ocr_image(content: bytes) -> dict:
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
