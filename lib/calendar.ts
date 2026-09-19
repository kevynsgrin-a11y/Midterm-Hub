type DatedElection = { election_date: string; state: string; id: string };

/** Civil dates are inclusive: an election stays listed throughout that day.
 * This is a calendar view, not a claim about local poll-closing times. */
export function upcomingElections<T extends DatedElection>(records: readonly T[], today: string, limit = 3): T[] {
  return records.filter((record) => record.election_date >= today)
    .sort((a, b) => a.election_date.localeCompare(b.election_date) || a.state.localeCompare(b.state) || a.id.localeCompare(b.id))
    .slice(0, limit);
}

export function localCalendarDate(now = new Date()): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
