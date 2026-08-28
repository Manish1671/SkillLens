const FALLBACK = "/";

/** Allow only same-origin relative paths used as post-login redirects. */
export function safeInternalPath(raw: string | null | undefined): string {
  if (!raw) return FALLBACK;
  const path = raw.trim();
  if (!path.startsWith("/")) return FALLBACK;
  if (path.startsWith("//")) return FALLBACK;
  if (path.startsWith("/\\")) return FALLBACK;
  if (path.includes("://")) return FALLBACK;
  if (path.includes("\n") || path.includes("\r")) return FALLBACK;
  return path;
}

export function loginHref(nextPath: string): string {
  return `/login?next=${encodeURIComponent(safeInternalPath(nextPath))}`;
}
