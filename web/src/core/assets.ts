/**
 * Static asset URL helper — prefixes Vite BASE_URL so the app works both at
 * the domain root ("/") and under a sub-path deployment (e.g. "/onemore/").
 */
export function assetURL(path: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

/** Full-page jump that keeps the Vite base path (e.g. /onemore/auth). */
export function appHref(path: string): string {
  return assetURL(path);
}
