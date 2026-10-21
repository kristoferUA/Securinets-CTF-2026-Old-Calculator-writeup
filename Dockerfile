ARG PYTHON_IMAGE=python:3.12.15-slim-bookworm
FROM ${PYTHON_IMAGE}

LABEL org.opencontainers.image.title="Old Calculator local instance" \
      org.opencontainers.image.authors="kristoferUA" \
      org.opencontainers.image.description="Securinets Old Calculator observed TCP protocol"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LISTEN_HOST=0.0.0.0 \
    PORT=4873

WORKDIR /app
COPY --chown=10001:10001 server.py healthcheck.py solve.py /app/
COPY --chown=10001:10001 fixtures /app/fixtures

USER 10001:10001
EXPOSE 4873/tcp
HEALTHCHECK --interval=10s --timeout=3s --start-period=2s --retries=3 \
    CMD ["python", "/app/healthcheck.py"]
CMD ["python", "/app/server.py"]
