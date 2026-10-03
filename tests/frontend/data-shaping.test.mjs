import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { importFromRepo } from './resolve-repo.mjs';

const payload = JSON.parse(readFileSync(new URL('../../generated/elections.json', import.meta.url)));
const elections = payload.elections;

const { elections: dataElections, stateNames, states, forState, findElection, electionHref, formatDate, titleCase } =
  await importFromRepo('../../lib/data.ts');

test('the published election index is the edition payload verbatim', () => {
  assert.ok(elections.length > 0, 'the edition must ship at least one election record');
  // Compared by value: the module resolves the JSON through the loader, so it
  // holds its own parse of the same file rather than this test's parse.
  assert.deepEqual(dataElections, elections);
  assert.equal(dataElections.length, elections.length);
});

test('the state index is de-duplicated by code and ordered by state name', () => {
  const codes = states.map(([code]) => code);
  assert.equal(new Set(codes).size, codes.length, 'a state must not appear twice');
  assert.equal(codes.length, new Set(elections.map((e) => e.state)).size);
  assert.equal(new Set(codes).size, Object.keys(stateNames).length);

  const names = states.map(([, name]) => name);
  assert.deepEqual(names, [...names].sort((a, b) => a.localeCompare(b)));
  for (const [code, name] of states) {
    assert.ok(name && name.length > 0, `state ${code} needs a display name`);
    assert.ok(elections.some((e) => e.state === code), `state ${code} has no election record`);
  }
});

test('a state lookup returns only that state, ordered by date, leaving the source untouched', () => {
  const before = dataElections.map((e) => e.id);
  for (const [code] of states) {
    const items = forState(code);
    assert.ok(items.every((e) => e.state === code), `${code} lookup leaked another state`);
    const dates = items.map((e) => e.election_date);
    assert.deepEqual(dates, [...dates].sort(), `${code} lookup is not date-ordered`);
  }
  assert.deepEqual(dataElections.map((e) => e.id), before, 'filtering must not reorder the shared payload');
});

test('an unknown state code yields an empty desk rather than a whole-country list', () => {
  assert.deepEqual(forState('ZZ'), []);
  assert.deepEqual(forState(''), []);
  assert.deepEqual(forState('ca'), [], 'lookup is by canonical uppercase code, not a loose match');
});

test('election lookup resolves a known id and reports nothing for an unknown one', () => {
  for (const election of elections) {
    const found = findElection(election.id);
    assert.deepEqual(found, election);
    assert.equal(found.id, election.id);
  }
  assert.equal(findElection('not-a-real-id'), undefined);
  assert.equal(findElection(''), undefined);
});

test('an election href is the route the static export actually emits', () => {
  const election = elections[0];
  assert.equal(
    electionHref(election),
    `/elections/${election.state}/${election.slug}/${election.id}/`
  );
  // Election directories keep their original uppercase state code; only /states/ is lowercased.
  assert.match(electionHref(election), /^\/elections\/[A-Z]{2}\//);
  assert.equal(new Set(elections.map(electionHref)).size, elections.length, 'election routes must be unique');
});

test('a date renders in full and compact form, and neither drifts across time zones', () => {
  assert.equal(formatDate('2026-11-03'), 'Tuesday, November 3, 2026');
  assert.equal(formatDate('2026-11-03', true), 'Nov 3');
  // The formatter anchors at UTC noon, so the civil date survives any local offset.
  assert.match(formatDate('2026-01-01'), /^Thursday, January 1, 2026$/);
  assert.match(formatDate('2026-12-31'), /^Thursday, December 31, 2026$/);
  assert.equal(formatDate('2026-11-03', false), formatDate('2026-11-03'));
});

test('snake_case election types read as titles without mangling inner words', () => {
  assert.equal(titleCase('general'), 'General');
  assert.equal(titleCase('general_election'), 'General Election');
  assert.equal(titleCase('special_election_runoff'), 'Special Election Runoff');
  assert.equal(titleCase(''), '');
});

test('every election type in the payload title-cases into a presentable label', () => {
  for (const election of elections) {
    const label = titleCase(election.election_type);
    assert.ok(label.length > 0, `${election.id} has no readable election type`);
    assert.ok(!label.includes('_'), `${election.id} label still contains an underscore`);
  }
});
