import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { splitNoteLinks } from "../../lib/note-links.mjs";

// One list of cases for both implementations: tests/test_site_base.py reads the same file.
const cases = JSON.parse(readFileSync(new URL("../fixtures/note_link_cases.json", import.meta.url), "utf8"));
const payload = JSON.parse(readFileSync(new URL("../../generated/elections.json", import.meta.url), "utf8"));
const page = readFileSync(new URL("../../app/elections/[state]/[slug]/[id]/page.tsx", import.meta.url), "utf8");

for (const { name, text, parts } of cases) {
  test(`note links: ${name}`, () => {
    const actual = splitNoteLinks(text);
    assert.deepEqual(actual, parts);
    // Nothing is dropped or invented: the parts rejoin to the note.
    assert.equal(actual.map((part) => part.text).join(""), text);
  });
}

test("note links: missing notes have no parts", () => {
  for (const empty of [undefined, null, ""]) assert.deepEqual(splitNoteLinks(empty), []);
});

test("every URL in a published note becomes exactly one link that rejoins to the unchanged note", () => {
  for (const election of payload.elections) {
    const note = election.notes ?? "";
    const parts = splitNoteLinks(note);
    assert.equal(parts.map((part) => part.text).join(""), note, `${election.id} must rejoin`);
    const links = parts.filter((part) => part.href);
    assert.equal(links.length, (note.match(/https?:\/\//gi) ?? []).length, `${election.id}: every URL in the note must be a link`);
    for (const link of links) assert.equal(link.href, link.text, `${election.id}: link text is the URL itself`);
  }
});

test("the election page prints notes through NoteText, never as a raw string", () => {
  assert.match(page, /<NoteText text=\{e\.notes\}\/>/);
  assert.doesNotMatch(page, /\{e\.notes\}<\/p>/);
});
