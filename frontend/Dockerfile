FROM node:22-alpine AS build

WORKDIR /app

# deploy.ps1 can stage Windows enterprise TLS interception certificates (for
# example Zscaler) before npm makes any network request. NODE_EXTRA_CA_CERTS
# augments Node's normal public CA set instead of replacing it.
COPY certs/ /opt/identityai/certs/
RUN set -eu; \
    : > /opt/identityai/extra-ca.crt; \
    for cert in /opt/identityai/certs/*.crt; do \
      [ -f "$cert" ] || continue; \
      cat "$cert" >> /opt/identityai/extra-ca.crt; \
      printf '\n' >> /opt/identityai/extra-ca.crt; \
    done

ENV NODE_EXTRA_CA_CERTS=/opt/identityai/extra-ca.crt

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O - http://127.0.0.1:8080/healthz >/dev/null 2>&1 || exit 1
