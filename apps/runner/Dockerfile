ARG PYTHON_BASE_IMAGE=docker.io/library/python:3.12.13-slim-trixie
FROM ${PYTHON_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m pip install --no-cache-dir \
    fastapi==0.141.1 \
    httpx==0.28.1 \
    python-multipart==0.0.22

COPY harness.py /opt/runner/harness.py

USER 65532:65532
WORKDIR /tmp
ENTRYPOINT ["python", "/opt/runner/harness.py"]
