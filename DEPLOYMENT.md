# IdentityAI Deployment

IdentityAI supports two deployment modes designed to avoid manual environment and SSL troubleshooting.

- **LAN/demo mode**: one-command HTTP deployment for laptops, internal demos, and test servers. No TLS certificate is required.
- **HTTPS mode**: production deployment behind Caddy. A real DNS hostname receives a browser-trusted TLS certificate automatically and Caddy renews it automatically.

The deployment scripts keep `backend/.env` as the single private configuration file. Secrets are generated automatically when missing. Never commit `backend/.env`.

## Prerequisite

Install and start **Docker Desktop**. No local Python, Node.js, PostgreSQL, or Nginx installation is required.

Rudrix is optional. If AI is required, install Ollama on the host. The deployment script can pull the expected models with `-SetupAI`.

## Windows: easiest deployment

From the repository root, double-click:

```text
deploy.bat
```

or run:

```powershell
.\deploy.ps1
```

The script automatically:

1. checks Docker and Docker Compose;
2. detects common corporate TLS interception certificates such as Zscaler from the Windows certificate store and stages them for the Docker builds;
3. creates `backend/.env` if it does not exist;
4. generates a PostgreSQL password if missing;
5. generates a secure authentication secret if missing;
6. sets Docker database networking to `DATABASE_HOST=postgres`;
7. detects the Windows hostname and LAN IPv4 address;
8. configures allowed hosts and same-origin browser access;
9. validates Docker Compose before starting;
10. builds and starts PostgreSQL, backend, and frontend;
11. waits for PostgreSQL, backend, and frontend health checks;
12. opens the application after a successful deployment.

### Corporate SSL / Zscaler

On corporate machines, HTTPS inspection products can replace the public certificate chain with an enterprise CA. That certificate is trusted by Windows, but a Linux Docker build does not automatically inherit the Windows trust store. This can cause errors such as:

```text
CERTIFICATE_VERIFY_FAILED
unable to get local issuer certificate
files.pythonhosted.org
```

`deploy.ps1` now searches the Windows Root and Intermediate CA stores for common enterprise interception products, including Zscaler, and writes the detected CA certificates into the backend/frontend Docker build contexts. The Python build uses the staged CA bundle for `pip`, the Node build uses it for `npm`, and the backend keeps the same CA bundle for runtime HTTPS calls.

Generated certificate files are ignored by Git and are never committed.

If the company uses a CA that is not detected automatically, provide it explicitly:

```powershell
.\deploy.ps1 -CorporateCaPath C:\certs\company-root.cer
```

PEM certificate files are also accepted:

```powershell
.\deploy.ps1 -CorporateCaPath C:\certs\company-root.crt
```

To disable automatic enterprise CA discovery:

```powershell
.\deploy.ps1 -SkipCorporateCaAutoDetect
```

This replaces the old insecure workaround of disabling certificate verification or adding `pip --trusted-host` flags.

## LAN/demo URL

The default local URL is:

```text
http://localhost:8080
```

The script also prints the LAN URL, for example:

```text
http://192.168.1.25:8080
```

To allow Windows Firewall automatically, run PowerShell as Administrator:

```powershell
.\deploy.ps1 -OpenFirewall
```

To use another host port:

```powershell
.\deploy.ps1 -Port 8090
```

## Rudrix / Ollama

The core IdentityAI application does not fail deployment when Ollama is unavailable.

To deploy and ensure the configured models are present:

```powershell
.\deploy.ps1 -SetupAI
```

This checks for Ollama and pulls:

```text
llama3.1:8b
nomic-embed-text
```

The Docker backend connects to host Ollama through:

```text
http://host.docker.internal:11434
```

If Ollama is unavailable, the script reports a warning while leaving the core application healthy.

## Production HTTPS without manual certificates

Use a real DNS hostname that resolves to the deployment machine, for example:

```text
identity.example.com
```

Then run:

```powershell
.\deploy.ps1 -Mode https -Domain identity.example.com
```

If Windows Firewall should be configured automatically, run PowerShell as Administrator:

```powershell
.\deploy.ps1 -Mode https -Domain identity.example.com -OpenFirewall
```

HTTPS mode automatically:

- switches the backend to production runtime settings;
- generates/preserves a strong authentication secret;
- enables secure authentication cookies;
- limits the backend allowed host to the configured DNS name;
- binds the direct frontend maintenance port to loopback only;
- starts Caddy on TCP 80/443;
- obtains a trusted certificate automatically;
- renews the certificate automatically;
- proxies HTTPS traffic to the internal frontend service.

The public URL becomes:

```text
https://identity.example.com
```

### HTTPS requirements

For automatic public certificates:

1. the DNS A/AAAA record must resolve to the deployment machine/public gateway;
2. inbound TCP 80 and 443 must reach the machine;
3. outbound internet access must allow Caddy to contact a public ACME certificate authority.

No certificate files need to be copied into the repository or manually renewed.

### Internal-only HTTPS

A browser-trusted certificate for a private IP or private-only hostname cannot be made universally trusted without either a corporate/private CA or installing trust on client machines. For isolated demos and LAN testing, use LAN mode and avoid TLS entirely. For enterprise internal HTTPS, terminate TLS with the organization's trusted reverse proxy or internal PKI.

This avoids the unreliable self-signed-certificate workflow that causes browser and connector SSL errors on other systems.

## Monitoring

Add `-Monitoring` to either deployment mode:

```powershell
.\deploy.ps1 -Monitoring
```

Prometheus is then exposed on:

```text
http://localhost:9090
```

For production, monitoring access should be restricted according to the organization's operational controls.

## Re-deploy after an update

After pulling new code, run the same command again:

```powershell
git pull
.\deploy.ps1
```

For HTTPS:

```powershell
git pull
.\deploy.ps1 -Mode https -Domain identity.example.com
```

Existing PostgreSQL data and generated secrets are retained.

## Health and troubleshooting

Check services:

```powershell
docker compose --env-file backend/.env ps
```

Backend logs:

```powershell
docker compose --env-file backend/.env logs --tail=200 backend
```

PostgreSQL logs:

```powershell
docker compose --env-file backend/.env logs --tail=200 postgres
```

Browser health endpoints:

```text
http://localhost:8080/api/health/live
http://localhost:8080/api/health/ready
```

The deployment script already performs these startup health checks and prints recent service logs when a container fails.

## Stop the stack

LAN deployment:

```powershell
docker compose --env-file backend/.env down
```

HTTPS deployment:

```powershell
docker compose --env-file backend/.env -f docker-compose.yml -f docker-compose.https.yml down
```

The PostgreSQL volume is retained.

Do **not** use `down -v` unless you intentionally want to delete the Docker database.

## Data note

Docker PostgreSQL data is stored in a named Docker volume. It is separate from any PostgreSQL instance installed directly on Windows.

A fresh deployment starts with an empty migrated database. Moving an existing environment to another machine requires an explicit database backup/restore process; the deployment script intentionally does not silently overwrite or copy database data.
