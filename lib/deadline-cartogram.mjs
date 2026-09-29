export const DEADLINE_BANDS = Object.freeze([
  Object.freeze({ id: "within-7", label: "≤ 7", maxDays: 7, fillToken: "--deadline-fill-7", textToken: "--deadline-text-7" }),
  Object.freeze({ id: "8-14", label: "8–14", maxDays: 14, fillToken: "--deadline-fill-14", textToken: "--deadline-text-14" }),
  Object.freeze({ id: "15-21", label: "15–21", maxDays: 21, fillToken: "--deadline-fill-21", textToken: "--deadline-text-21" }),
  Object.freeze({ id: "22-30", label: "22–30", maxDays: 30, fillToken: "--deadline-fill-30", textToken: "--deadline-text-30" }),
  Object.freeze({ id: "over-30", label: "> 30", maxDays: Number.POSITIVE_INFINITY, fillToken: "--deadline-fill-over-30", textToken: "--deadline-text-over-30" }),
]);

export const NULL_DEADLINE_HATCH = "repeating-linear-gradient(45deg, var(--muted) 0 2px, transparent 2px 6px)";

export function deadlineBand(days) {
  if (days === null || !Number.isFinite(days)) return null;
  return DEADLINE_BANDS.find((band) => days <= band.maxDays) ?? null;
}

export function tileFill(days) {
  const band = deadlineBand(days);
  if (!band) {
    return {
      band: null,
      style: { backgroundImage: NULL_DEADLINE_HATCH, color: "var(--foreground)" },
    };
  }

  return {
    band,
    style: {
      backgroundColor: `var(${band.fillToken})`,
      color: `var(${band.textToken})`,
    },
  };
}

export function nullDeadlineLabel(state) {
  if (state === "ND") return "North Dakota does not require voter registration";
  if (state === "NH") return "Registration deadlines vary by municipality (6–13 days before Election Day)";
  return "Registration deadline pending in this edition";
}
