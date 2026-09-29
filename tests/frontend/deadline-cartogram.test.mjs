import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  DEADLINE_BANDS,
  deadlineBand,
  nullDeadlineLabel,
  tileFill,
} from "../../lib/deadline-cartogram.mjs";

const css = await readFile(new URL("../../app/globals.css", import.meta.url), "utf8");
const component = await readFile(new URL("../../components/data-art.tsx", import.meta.url), "utf8");

function blockAfter(text, marker) {
  const start = text.indexOf(marker);
  assert.notEqual(start, -1, `Missing CSS block: ${marker}`);
  const open = text.indexOf("{", start);
  const close = text.indexOf("}", open);
  assert.notEqual(close, -1, `Unclosed CSS block: ${marker}`);
  return text.slice(open + 1, close);
}

function cssColor(block, token) {
  const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = block.match(new RegExp(`${escaped}:\\s*(#[0-9a-f]{6})`, "i"));
  assert.ok(match, `Missing ${token} in CSS theme`);
  return match[1];
}

function luminance(hex) {
  const channels = [1, 3, 5].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16) / 255);
  const linear = channels.map((channel) => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4);
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrastRatio(first, second) {
  const values = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

test("deadline thresholds cover each rendered boundary with one shared five-band scale", () => {
  assert.deepEqual(DEADLINE_BANDS.map(({ label }) => label), ["≤ 7", "8–14", "15–21", "22–30", "> 30"]);
  const boundaries = [
    [-1, "within-7"], [0, "within-7"], [7, "within-7"], [8, "8-14"], [14, "8-14"],
    [15, "15-21"], [21, "15-21"], [22, "22-30"], [30, "22-30"], [31, "over-30"],
  ];
  for (const [days, id] of boundaries) assert.equal(deadlineBand(days)?.id, id, `${days} days`);
  assert.equal(deadlineBand(null), null);
  assert.match(component, /DEADLINE_BANDS\.map\(/, "The legend should render directly from the scale used by tiles");
  assert.match(component, /tileFill\(tile\?\.days \?\? null\)/, "Each tile should use the tested scale");
});

test("each tile fill and text pair meets WCAG AA contrast in light and dark themes", () => {
  const lightTheme = blockAfter(css, ":root {");
  const darkTheme = blockAfter(css, "@media (prefers-color-scheme: dark)");

  for (const band of DEADLINE_BANDS) {
    const tile = tileFill(band.maxDays === Number.POSITIVE_INFINITY ? 31 : band.maxDays);
    assert.equal(tile.style.backgroundColor, `var(${band.fillToken})`);
    assert.equal(tile.style.color, `var(${band.textToken})`);

    for (const theme of [lightTheme, darkTheme]) {
      const fill = cssColor(theme, band.fillToken);
      const text = cssColor(theme, band.textToken);
      const ratio = contrastRatio(fill, text);
      assert.ok(ratio >= 4.5, `${band.label} contrast is ${ratio.toFixed(2)}:1 for ${fill} / ${text}`);
    }
  }
});

test("null deadlines preserve New Hampshire's municipal timing and distinguish North Dakota", () => {
  assert.equal(
    nullDeadlineLabel("NH"),
    "Registration deadlines vary by municipality (6–13 days before Election Day)",
  );
  assert.equal(nullDeadlineLabel("ND"), "North Dakota does not require voter registration");
  assert.equal(nullDeadlineLabel("XX"), "Registration deadline pending in this edition");
  assert.match(component, /NH registration timing varies by municipality \(6–13 days before Election Day\)/);
});
