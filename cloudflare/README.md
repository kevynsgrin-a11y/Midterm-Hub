# Cloudflare domain edge

The site is built and deployed by v0/Vercel at `midterm-hub.vercel.app`.
This Worker attaches the Cloudflare-managed `midtermwatch.com` zone to that
deployment while keeping `https://midtermwatch.com` as the canonical URL.

Deploy from the repository root:

```sh
npx wrangler deploy --config cloudflare/wrangler.jsonc
```

Cloudflare Custom Domains create the DNS records and TLS certificates for the
apex and `www` hosts. Requests to `www` are permanently redirected to the apex.
