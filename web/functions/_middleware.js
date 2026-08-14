const ORIGIN = "https://lulu.classby.cn/onemore";

function keepOnPages(pathname) {
  if (pathname === "/" || pathname === "") return true;
  if (pathname.startsWith("/legal")) return true;
  if (pathname.startsWith("/assets/")) return true;
  if (pathname === "/favicon.svg" || pathname === "/icons.svg") return true;
  return false;
}

/** Marketing stays on Pages; product routes jump to the origin web app. */
export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (keepOnPages(url.pathname)) return context.next();
  return Response.redirect(`${ORIGIN}${url.pathname}${url.search}`, 302);
}
