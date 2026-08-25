const DEFAULT_API_BASE_URL =
  `${window.location.protocol}//${window.location.hostname}:8000/api`;

const configuredApiBaseUrl =
  import.meta.env.VITE_API_BASE_URL?.trim();

/**
 * Single frontend API base URL.
 *
 * Configure deployments with VITE_API_BASE_URL in frontend/.env.
 * The fallback keeps local development working when no env file exists.
 */
export const API_BASE_URL = (
  configuredApiBaseUrl || DEFAULT_API_BASE_URL
).replace(/\/+$/, "");
