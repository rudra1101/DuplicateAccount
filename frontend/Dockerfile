FROM node:22-alpine AS build

WORKDIR /app

RUN apk add --no-cache ca-certificates

# deploy.ps1 can stage Windows enterprise interception certificates (for
# example Zscaler) in frontend/certs before npm downloads dependencies.
COPY certs/ /usr/local/share/ca-certificates/identityai/
RUN if find /usr/local/share/ca-certificates/identityai -type f -name '*.crt' -print -quit | grep -q .; then \
      update-ca-certificates; \
    fi

ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt \
    NPM_CONFIG_CAFILE=/etc/ssl/certs/ca-certificates.crt

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
