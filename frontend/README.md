# DuplicateAccount Frontend

React + Vite frontend for the Duplicate Account Detection platform.

## Local setup

Install dependencies and start Vite:

```bash
npm install
npm run dev
```

## API configuration

The frontend API URL is configured through a single Vite environment variable.

1. Copy `.env.example` to `.env`.
2. Set the backend API base URL:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

All frontend services read the shared value from `src/config/api.ts`. When the backend host, protocol, port, or API prefix changes, update `VITE_API_BASE_URL` rather than editing individual service files.

A local-development fallback is retained in `src/config/api.ts` so the frontend still works when `.env` is absent.
