import payload from "@/generated/elections.json";

export type Election = {
  id: string; state: string; state_name: string; jurisdiction_type: string;
  jurisdiction_name: string; election_type: string; election_date: string;
  offices: string[]; confidence: "official" | "secondary" | "inferred";
  source_url: string; source_retrieved_at?: string | null; notes?: string | null;
  registration_deadline?: string | null; early_voting_start?: string | null;
  early_voting_end?: string | null; mail_ballot_request_deadline?: string | null;
  candidate_filing_deadline?: string | null; slug: string; verified: boolean;
};

export const data = payload as { edition: string; generated_at: string; demo: boolean; elections: Election[] };
export const elections = data.elections;
export const stateNames = Object.fromEntries(elections.map((e) => [e.state, e.state_name]));
export const states = Object.entries(stateNames).sort((a, b) => a[1].localeCompare(b[1]));
export const electionHref = (e: Election) => `/elections/${e.state}/${e.slug}/${e.id}/`;
export const stateHref = (code: string) => `/states/${code}/`;
export const formatDate = (date: string, compact = false) => new Intl.DateTimeFormat("en-US", compact ? { month: "short", day: "numeric" } : { weekday: "long", month: "long", day: "numeric", year: "numeric" }).format(new Date(`${date}T12:00:00Z`));
export const titleCase = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
export const forState = (code: string) => elections.filter((e) => e.state === code).sort((a,b) => a.election_date.localeCompare(b.election_date));
export const findElection = (id: string) => elections.find((e) => e.id === id);
