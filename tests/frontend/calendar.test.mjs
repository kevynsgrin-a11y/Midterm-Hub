import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { upcomingElections, localCalendarDate } from '../../lib/calendar.ts';
import { stateHref } from '../../lib/navigation.ts';
import proxy from '../../cloudflare/src/worker.js';

const elections = JSON.parse(readFileSync(new URL('../../generated/elections.json', import.meta.url))).elections;

test('September calendar excludes past primaries but retains the general election', () => {
  const upcoming = upcomingElections(elections, '2026-09-18');
  assert.equal(upcoming.length, 3);
  assert.ok(upcoming.every(e => e.election_date >= '2026-09-18'));
  assert.ok(upcoming.some(e => e.election_type === 'general'));
});

test('date boundary includes today, sorts independent of input, then expires', () => {
  const records = [{id:'later', state:'CA', election_date:'2026-11-04'}, {id:'today', state:'CA', election_date:'2026-11-03'}, {id:'past', state:'CA', election_date:'2026-11-02'}];
  assert.deepEqual(upcomingElections(records, '2026-11-03').map(e => e.id), ['today', 'later']);
  assert.deepEqual(upcomingElections(records, '2026-11-04').map(e => e.id), ['later']);
  assert.deepEqual(upcomingElections(records, '2026-11-05'), []);
  assert.equal(records[0].id, 'later');
  assert.equal(localCalendarDate(new Date(2026, 0, 2, 23, 59)), '2026-01-02');
});

test('every recorded state uses the lowercase generated route', () => {
  for (const code of new Set(elections.map(e => e.state))) {
    assert.equal(stateHref(code), `/states/${code.toLowerCase()}/`);
    assert.equal(stateHref(code.toLowerCase()), stateHref(code));
  }
});

test('legacy uppercase state links permanently redirect and keep query strings', async () => {
  for (const host of ['midtermwatch.com', 'www.midtermwatch.com']) {
    const response = await proxy.fetch(new Request(`https://${host}/states/CA/?ref=calendar`));
    assert.equal(response.status, 308);
    assert.equal(response.headers.get('location'), 'https://midtermwatch.com/states/ca/?ref=calendar');
  }
});

test('election routes retain their original uppercase codes', async () => {
  const original = globalThis.fetch;
  let forwarded;
  globalThis.fetch = async request => { forwarded = request.url; return new Response('OK'); };
  try {
    const response = await proxy.fetch(new Request('https://midtermwatch.com/elections/CA/california/id/'));
    assert.equal(response.status, 200);
    assert.equal(forwarded, 'https://midterm-hub.vercel.app/elections/CA/california/id/');
  } finally { globalThis.fetch = original; }
});
