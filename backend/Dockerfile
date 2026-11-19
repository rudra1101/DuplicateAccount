FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# deploy.ps1 can stage Windows enterprise TLS interception certificates (for
# example Zscaler) before this image is built. Build a CA bundle before pip
# makes any network request so corporate HTTPS inspection does not break the
# dependency install. The same bundle remains available to Python at runtime.
COPY certs/ /opt/identityai/certs/
RUN set -eu; \
    bundle=/opt/identityai/ca-bundle.crt; \
    default_ca="$(python -c 'import ssl; print(ssl.get_default_verify_paths().cafile or "")')"; \
    if [ -n "$default_ca" ] && [ -f "$default_ca" ]; then \
        cat "$default_ca" > "$bundle"; \
    else \
        : > "$bundle"; \
    fi; \
    for cert in /opt/identityai/certs/*.crt; do \
        [ -f "$cert" ] || continue; \
        cat "$cert" >> "$bundle"; \
        printf '\n' >> "$bundle"; \
    done

ENV PIP_CERT=/opt/identityai/ca-bundle.crt \
    REQUESTS_CA_BUNDLE=/opt/identityai/ca-bundle.crt \
    SSL_CERT_FILE=/opt/identityai/ca-bundle.crt

RUN groupadd --system identityai \
    && useradd --system --gid identityai --home-dir /app identityai

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=identityai:identityai . .

# Normalize Windows CRLF checkouts before executing the Linux entrypoint.
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh \
    && chmod +x /app/docker-entrypoint.sh

USER identityai

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/live', timeout=3).read()" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
