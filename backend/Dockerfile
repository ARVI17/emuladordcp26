FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PYTHONPATH=/app
RUN apt-get update && apt-get install -y --no-install-recommends adb tesseract-ocr tesseract-ocr-spa libgl1 libglib2.0-0 postgresql-client && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ARG BUILD_REVISION=unknown
ARG BUILD_DATE=unknown
ARG BUILD_ENVIRONMENT=development
ARG BUILD_DIRTY=false
ENV BUILD_REVISION=$BUILD_REVISION BUILD_DATE=$BUILD_DATE BUILD_ENVIRONMENT=$BUILD_ENVIRONMENT BUILD_DIRTY=$BUILD_DIRTY
RUN python -c "import os,json; from pathlib import Path; Path('/app/build.json').write_text(json.dumps(dict(edition='FC27',revision=os.environ['BUILD_REVISION'],built_at=os.environ['BUILD_DATE'],environment=os.environ['BUILD_ENVIRONMENT'],source_dirty=os.environ['BUILD_DIRTY']=='true')))"
LABEL org.opencontainers.image.revision=$BUILD_REVISION org.opencontainers.image.created=$BUILD_DATE app.edition=FC27 app.environment=$BUILD_ENVIRONMENT app.source_dirty=$BUILD_DIRTY
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
