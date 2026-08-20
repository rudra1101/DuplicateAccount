const BACKEND_ORIGINS = new Set([
  "http://127.0.0.1:8000",
  "http://localhost:8000",
]);

let installed = false;

export function installAuthenticatedFetch() {
  if (installed) {
    return;
  }

  installed = true;
  const originalFetch = window.fetch.bind(window);

  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    let url: URL | null = null;

    try {
      if (typeof input === "string" || input instanceof URL) {
        url = new URL(input.toString(), window.location.origin);
      } else {
        url = new URL(input.url, window.location.origin);
      }
    } catch {
      url = null;
    }

    if (url && BACKEND_ORIGINS.has(url.origin)) {
      return originalFetch(input, {
        ...init,
        credentials: "include",
      });
    }

    return originalFetch(input, init);
  };
}
