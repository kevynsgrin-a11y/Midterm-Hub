# Deploying midtermwatch.com

The site is a hermetic static build. One command produces the whole thing:

```bash
bash scripts/build-site.sh dist    # → ./dist, built for https://midtermwatch.com
```

`dist/` contains the full site (HTML, `/assets`, `/downloads`, `sitemap.xml`,
`robots.txt`, and a `CNAME` file). Pick one host below.

> The current build uses the clearly-fake **sample** dataset and shows a
> "Demonstration site" banner. To go live with real data: add real intake files and
> run `civic intake …`, then drop `--demo` in `scripts/build-site.sh`.

---

## Option A — Cloudflare Pages (recommended, since the domain is on Cloudflare)

In the Cloudflare dashboard → **Workers & Pages → Create → Pages → Connect to Git**,
select this repo and set:

| Setting | Value |
| --- | --- |
| Build command | `bash scripts/build-site.sh dist` |
| Build output directory | `dist` |
| Environment variable | `PYTHON_VERSION = 3.11` |

Then **Custom domains → Set up a domain → `midtermwatch.com`**. Cloudflare adds the
DNS records automatically because the zone is already in your account. Every push to
`main` redeploys. (The `CNAME` file in `dist/` is ignored by Cloudflare Pages and is
harmless.)

## Option B — GitHub Pages + Cloudflare DNS

`.github/workflows/deploy-site.yml` already builds and deploys on push to `main`.
One-time setup:

1. **Repo → Settings → Pages → Source: "GitHub Actions".**
2. **Settings → Pages → Custom domain: `midtermwatch.com`** (this matches the `CNAME`
   the build emits). Leave "Enforce HTTPS" on once the cert provisions.
3. **In Cloudflare DNS**, add a record for the apex:
   - Type `CNAME`, Name `@` (or `midtermwatch.com`), Target `kevynsgrin-a11y.github.io`
     — Cloudflare flattens apex CNAMEs automatically.
   - Set it to **DNS only** (grey cloud) first while GitHub provisions the TLS cert;
     you can switch to **Proxied** (orange cloud) afterward.
4. Trigger a deploy: push to `main`, or **Actions → deploy-site → Run workflow**.

Live at `https://midtermwatch.com/`.

---

## Verifying a build locally

```bash
python -m http.server -d dist 8000   # then open http://localhost:8000/
```

Everything is same-origin and self-contained — no external requests.
