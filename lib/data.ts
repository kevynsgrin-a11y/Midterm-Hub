import payload from "@/generated/elections.json";

export type LateRegistration = "none" | "early_voting" | "election_day" | "not_required";

export type Election = {
  id: string; state: string; state_name: string; jurisdiction_type: string;
  jurisdiction_name: string; election_type: string; election_date: string;
  offices: string[]; confidence: "official" | "secondary" | "inferred";
  source_url: string; source_retrieved_at?: string | null; notes?: string | null;
  registration_deadline?: string | null; early_voting_start?: string | null;
  early_voting_end?: string | null; mail_ballot_request_deadline?: string | null;
  candidate_filing_deadline?: string | null; late_registration?: LateRegistration | null; slug: string; verified: boolean;
};

export const data = payload as { edition: string; generated_at: string; demo: boolean; elections: Election[] };
export const elections = data.elections;
export const stateNames = Object.fromEntries(elections.map((e) => [e.state, e.state_name]));
export const states = Object.entries(stateNames).sort((a, b) => a[1].localeCompare(b[1]));
// `states` also holds DC, so its length is jurisdictions (51), not states (50).
export const stateCount = states.filter(([code]) => code !== "DC").length;
// Jurisdictions (states and DC) that have a reviewed primary-election record in this edition.
export const primaryCoverage = new Set(elections.filter((e) => e.election_type === "primary").map((e) => e.state)).size;
// Shown beside the registration deadline; keep in step with LATE_REGISTRATION_LABELS in civic/downloads.py.
const lateRegistrationLabels = new Map<string, string>(Object.entries({
  none: "Closed after the deadline",
  early_voting: "Open during early voting",
  election_day: "Open through Election Day",
  not_required: "No registration required",
}));
export const lateRegistrationLabel = (value?: string | null) => (value ? lateRegistrationLabels.get(value) ?? null : null);
export const electionHref = (e: Election) => `/elections/${e.state}/${e.slug}/${e.id}/`;
export { stateHref } from "./navigation";
export const formatDate = (date: string, compact = false) => new Intl.DateTimeFormat("en-US", compact ? { month: "short", day: "numeric" } : { weekday: "long", month: "long", day: "numeric", year: "numeric" }).format(new Date(`${date}T12:00:00Z`));
export const titleCase = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
export const forState = (code: string) => elections.filter((e) => e.state === code).sort((a,b) => a.election_date.localeCompare(b.election_date));
export const findElection = (id: string) => elections.find((e) => e.id === id);
