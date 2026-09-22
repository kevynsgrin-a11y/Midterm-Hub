"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ElectionCard } from "@/components/election-card";
import { elections } from "@/lib/data";
import { localCalendarDate, upcomingElections } from "@/lib/calendar";

export function UpcomingElections({ initialDate }: { initialDate: string }) {
  // Use the build date for matching server/client first paint, then the visitor's
  // device date. Recheck after midnight and after returning to a sleeping tab.
  const [today, setToday] = useState(initialDate);
  useEffect(() => {
    const refresh = () => setToday(localCalendarDate());
    refresh();
    const timer = window.setInterval(refresh, 60_000);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, []);
  const upcoming = upcomingElections(elections, today);

  return <section className="border-y bg-card" aria-labelledby="upcoming-heading">
    <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8">
      <div className="flex items-end justify-between gap-4 border-b pb-6">
        <div><p className="rule-label">Next on the calendar</p><h2 id="upcoming-heading" className="mt-2 font-serif text-4xl font-bold">Upcoming elections</h2></div>
        <Link href="/states/" className="editorial-link text-sm">Full state index</Link>
      </div>
      <p className="mt-4 text-sm text-muted-foreground">Dates on or after <time dateTime={today}>{today}</time> in this edition. Calendar dates include today; confirm local voting hours with the official source.</p>
      <noscript><p className="mt-2 text-sm text-muted-foreground">This list reflects the build date above. Enable JavaScript to filter by your device date, or browse the full state index.</p></noscript>
      {upcoming.length ? <div className="mt-8 grid gap-5 md:grid-cols-3">{upcoming.map((e, index) => <ElectionCard key={e.id} election={e} featured={index === 0} />)}</div>
        : <p className="mt-8 border p-6">No upcoming elections are listed in this edition for that date. The state index retains past records and their official sources.</p>}
    </div>
  </section>;
}
