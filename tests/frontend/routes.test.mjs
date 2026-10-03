import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { importFromRepo } from './resolve-repo.mjs';

const payload = JSON.parse(readFileSync(new URL('../../generated/elections.json', import.meta.url)));
const elections = payload.elections;
const BASE = 'https://midtermwatch.com';

const { default: sitemap } = await importFromRepo('../../app/sitemap.ts');
const { default: robots } = await importFromRepo('../../app/robots.ts');

test('the sitemap publishes exactly the five standing pages under the canonical host', () => {
  const urls = sitemap().map((entry) => entry.url);
  for (const path of ['/states/', '/methodology/', '/data/', '/about/']) {
    assert.ok(urls.includes(BASE + path), `expected ${BASE}${path} in the sitemap`);
  }
  assert.equal(urls[0], BASE);
  assert.ok(urls.every((url) => url.startsWith(BASE)), 'no sitemap entry may point off the canonical host');
});

test('every state and election record is discoverable, once, through the sitemap', () => {
  const entries = sitemap();
  const urls = entries.map((entry) => entry.url);
  assert.equal(urls.length, 5 + new Set(elections.map((e) => e.state)).size + elections.length);
  assert.equal(new Set(urls).size, urls.length, 'the sitemap must not repeat a URL');

  for (const code of new Set(elections.map((e) => e.state))) {
    assert.ok(urls.includes(`${BASE}/states/${code.toLowerCase()}/`), `missing state route for ${code}`);
  }
  for (const election of elections) {
    assert.ok(
      urls.includes(`${BASE}/elections/${election.state}/${election.slug}/${election.id}/`),
      `missing election route for ${election.id}`
    );
  }
});

test('every sitemap entry carries a real modification timestamp', () => {
  for (const entry of sitemap()) {
    assert.ok(entry.lastModified instanceof Date, `${entry.url} has no Date lastModified`);
    assert.ok(!Number.isNaN(entry.lastModified.getTime()));
  }
});

test('robots allows every crawler and advertises the sitemap it just published', () => {
  const result = robots();
  assert.equal(result.rules.userAgent, '*');
  assert.equal(result.rules.allow, '/');
  assert.equal(result.sitemap, `${BASE}/sitemap.xml`);
  assert.ok(
    sitemap().map((entry) => entry.url).every((url) => url.startsWith(BASE)),
    'the advertised sitemap host must match the generated entries'
  );
});
