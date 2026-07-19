"""Static site generator (Product #1: the consumer directory).

Reads verified election records from the store and renders a complete, hermetic,
SEO-focused static website — no server, no external requests. This package is the
front-end companion to the file-only backend: same data-integrity discipline,
rendered for citizens.

Modules:
- ``data``: DB rows -> render-ready view models (design-independent).
- ``render``: HTML primitives, escaping, and the page/layout shell.
- ``components``: reusable UI fragments (cards, chips, badges, breadcrumbs).
- ``pages``: one renderer per page type.
- ``seo``: JSON-LD, sitemap.xml, robots.txt, meta tags.
- ``build``: orchestration — walks the data and writes every file.
"""
