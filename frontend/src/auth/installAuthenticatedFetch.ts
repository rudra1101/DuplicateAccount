const BACKEND_HOSTS = new Set(["127.0.0.1", "localhost"]);

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

    if (url && url.port === "8000" && BACKEND_HOSTS.has(url.hostname)) {
      url.hostname = window.location.hostname;

      const rewrittenInput =
        typeof input === "string" || input instanceof URL
          ? url.toString()
          : new Request(url.toString(), input);

      return originalFetch(rewrittenInput, {
        ...init,
        credentials: "include",
      });
    }

    return originalFetch(input, init);
  };
}
