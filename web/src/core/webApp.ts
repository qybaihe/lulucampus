/**
 * Product web app origin. Empty when landing and app share one SPA
 * (local `yarn dev`, origin `/onemore/`). Set `VITE_WEB_APP_ORIGIN` when
 * the marketing site is on Cloudflare Pages and the app stays on the
 * origin server.
 */
export function joinWebAppURL(origin: string | undefined, path = "/app"): string {
  const base = (origin ?? "").trim().replace(/\/$/, "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (!base) return normalized;
  return `${base}${normalized}`;
}

export function webAppURL(path = "/app"): string {
  return joinWebAppURL(import.meta.env.VITE_WEB_APP_ORIGIN, path);
}

export function isExternalWebApp(): boolean {
  return /^https?:\/\//i.test(webAppURL());
}
