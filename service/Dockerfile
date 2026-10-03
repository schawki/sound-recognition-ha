# Build from the repository root:  docker build -f service/Dockerfile -t sound-recognition-ha .
FROM python:3.12-slim

# YAMNet (Apache-2.0, Google) in TFLite format. The file is downloaded at build time and its SHA-256 is verified.
ARG MODEL_URL=https://raw.githubusercontent.com/larsyde/tflite-models-audioset-yamnet/master/yamnet.tflite
ARG MODEL_SHA256=e6814cb605db99bf7226a380c0b6708a9f4736c2c1e821a9ea5d3181f6ccf374

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/models \
    && curl -fsSL "$MODEL_URL" -o /opt/models/yamnet.tflite \
    && echo "$MODEL_SHA256  /opt/models/yamnet.tflite" | sha256sum -c -

WORKDIR /app
COPY service/pyproject.toml /app/pyproject.toml
COPY service/soundrec /app/soundrec
COPY catalog /app/catalog
RUN pip install --no-cache-dir .

ENV SOUNDREC_CATALOG=/app/catalog SOUNDREC_MODEL=/opt/models/yamnet.tflite SOUNDREC_CONFIG=/config/config.yaml
VOLUME ["/config", "/data"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s CMD curl -fs http://127.0.0.1:8765/api/v1/health || exit 1
CMD ["python", "-m", "soundrec"]
