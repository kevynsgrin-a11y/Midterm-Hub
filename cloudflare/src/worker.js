const UPSTREAM_ORIGIN = "https://midterm-hub.vercel.app";
const CANONICAL_ORIGIN = "https://midtermwatch.com";

function canonicalUrl(url) {
  return `${CANONICAL_ORIGIN}${url.pathname}${url.search}`;
}

function rewriteLocation(location, upstreamUrl) {
  if (!location) return null;

  const target = new URL(location, upstreamUrl);
  if (target.origin !== UPSTREAM_ORIGIN) return location;

  return canonicalUrl(target);
}

const worker = {
  async fetch(request) {
    const incomingUrl = new URL(request.url);

    // Old published links used uppercase state codes, but Next exports lowercase
    // directories. Normalize only this route family; election URLs stay intact.
    if (/^\/states\/[A-Za-z]{2}\/?$/.test(incomingUrl.pathname)) {
      const normalized = incomingUrl.pathname.toLowerCase().replace(/\/?$/, "/");
      if (incomingUrl.pathname !== normalized) {
        incomingUrl.pathname = normalized;
        return Response.redirect(canonicalUrl(incomingUrl), 308);
      }
    }

    if (incomingUrl.hostname === "www.midtermwatch.com") {
      return Response.redirect(canonicalUrl(incomingUrl), 308);
    }

    const upstreamUrl = new URL(incomingUrl.pathname + incomingUrl.search, UPSTREAM_ORIGIN);
    const upstreamRequest = new Request(upstreamUrl, request);
    const upstreamResponse = await fetch(upstreamRequest, { redirect: "manual" });
    const headers = new Headers(upstreamResponse.headers);
    const location = rewriteLocation(headers.get("location"), upstreamUrl);

    if (location) headers.set("location", location);

    return new Response(upstreamResponse.body, {
      status: upstreamResponse.status,
      statusText: upstreamResponse.statusText,
      headers,
    });
  },
};

export default worker;
