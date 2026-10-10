// Splits free-text record notes into plain and linked parts so a bare http(s) URL renders as an anchor.
// Keep the rules in step with split_note_links() in civic/site/base.py; both read tests/fixtures/note_link_cases.json.
const URL_PATTERN = /(?<![A-Za-z0-9])https?:\/\/[^\s<>"'`\u2018\u2019\u201c\u201d]+/gi;
const SENTENCE_PUNCTUATION = ".,;:!?";
const OPENING_BRACKET = { ")": "(", "]": "[", "}": "{" };

const occurrences = (text, char) => text.split(char).length - 1;

// Drop what ends the sentence rather than the URL: trailing . , ; : ! ? and any closing bracket that has no
// opening bracket inside the URL, so "(see https://x.gov/a)" loses the ")" but "https://x.gov/Foo_(bar)" keeps it.
function trimUrl(url) {
  let end = url.length;
  while (end > 0) {
    const last = url[end - 1];
    const head = url.slice(0, end);
    const strayCloser = Object.hasOwn(OPENING_BRACKET, last) && occurrences(head, last) > occurrences(head, OPENING_BRACKET[last]);
    if (SENTENCE_PUNCTUATION.includes(last) || strayCloser) end -= 1;
    else break;
  }
  return url.slice(0, end);
}

function isLinkable(url) {
  try {
    const { protocol, hostname } = new URL(url);
    return (protocol === "https:" || protocol === "http:") && hostname.length > 0;
  } catch {
    return false;
  }
}

// Only http(s) URLs with a host become links, so javascript:, data: and mailto: stay plain text.
// The parts always rejoin to the original string.
export function splitNoteLinks(text) {
  if (!text) return [];
  const parts = [];
  let cursor = 0;
  for (const match of text.matchAll(URL_PATTERN)) {
    const url = trimUrl(match[0]);
    if (!isLinkable(url)) continue;
    if (match.index > cursor) parts.push({ text: text.slice(cursor, match.index) });
    parts.push({ text: url, href: url });
    cursor = match.index + url.length;
  }
  if (cursor < text.length) parts.push({ text: text.slice(cursor) });
  return parts;
}
