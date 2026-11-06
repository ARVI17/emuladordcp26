"""Tesseract por tuberías: sin archivos de imagen temporales ni texto en logs."""
import csv
import io
import re
import subprocess
import time
from collections import defaultdict
from app.services.import_export import validate_image, _OCR_GATE, MAX_OCR_PIXELS


class ScanCancelled(Exception):
    pass


def recognize(content: bytes, cancelled=lambda: False):
    import cv2
    import numpy as np
    width, height = validate_image(content)
    if not _OCR_GATE.acquire(blocking=False):
        raise ValueError('OCR ocupado')
    process = None
    try:
        if cancelled():
            raise ScanCancelled()
        pixels = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_GRAYSCALE)
        scale = min(1.6, (MAX_OCR_PIXELS / (width * height)) ** .5)
        pixels = cv2.resize(pixels, None, fx=scale, fy=scale)
        pixels = cv2.threshold(pixels, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        encoded = cv2.imencode('.png', pixels)[1].tobytes()
        process = subprocess.Popen(['tesseract', 'stdin', 'stdout', '-l', 'spa+eng', '--psm', '6', 'tsv'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        started, first = time.monotonic(), True
        while True:
            if cancelled():
                raise ScanCancelled()
            if time.monotonic() - started > 10:
                raise ValueError('OCR agotó su tiempo')
            try:
                output, _ = process.communicate(input=encoded if first else None, timeout=.25)
                break
            except subprocess.TimeoutExpired:
                first = False
        if process.returncode or len(output) > 2_000_000:
            raise ValueError('OCR no disponible')
        lines = defaultdict(list)
        for word in csv.DictReader(io.StringIO(output.decode('utf-8', 'replace')), delimiter='\t', quoting=csv.QUOTE_NONE):
            if word.get('level') != '5' or not word.get('text', '').strip():
                continue
            key = tuple(word[k] for k in ('block_num', 'par_num', 'line_num'))
            lines[key].append((word['text'], max(0., min(1., float(word['conf']) / 100))))
        text_lines = [' '.join(w[0] for w in words) for words in lines.values()]
        confidences = {line: min(w[1] for w in words) for line, words in zip(text_lines, lines.values())}
        return {'text': '\n'.join(text_lines)[:12000], 'lines': confidences,
                'seconds': round(time.monotonic() - started, 3)}
    except (OSError, KeyError, csv.Error) as exc:
        raise ValueError('OCR no disponible') from None
    finally:
        if process:
            if process.poll() is None:
                process.kill()
            process.communicate()
        _OCR_GATE.release()


SENSITIVE = re.compile(r'password|contrase[nñ]a|iniciar sesi[oó]n|sign\s*in|log\s*in|\bmfa\b|\b2fa\b|'
    r'verification|verificaci[oó]n|autenticaci[oó]n|c[oó]digo de seguridad|correo electr[oó]nico|'
    r'@\w+[.]|access[_ -]?token|bearer\s|tarjeta de cr[eé]dito|credit card|\bcvv\b|'
    r'\bpagos?\b|\bpayment\b|datos personales|mi perfil|account settings', re.I)


def field_confidence(card, lines):
    # Confidence is OCR evidence, never probability that a card is correctly identified.
    matching = [score for line, score in lines.items() if card['name'].casefold() in line.casefold()]
    score = min(matching) if matching else 0.
    return dict(name=score, rating=score, position=score)
