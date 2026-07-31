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

export default {
  async fetch(request) {
    const incomingUrl = new URL(request.url);

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
