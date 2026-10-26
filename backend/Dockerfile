FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# deploy.ps1 can stage Windows enterprise interception certificates (for
# example Zscaler) in backend/certs before the image is built. Keep the
# directory present even when no custom certificate is required.
COPY certs/ /usr/local/share/ca-certificates/identityai/
RUN if find /usr/local/share/ca-certificates/identityai -type f -name '*.crt' -print -quit | grep -q .; then \
        update-ca-certificates; \
    fi

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
