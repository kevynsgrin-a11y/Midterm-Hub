import Link from "next/link";
import { ArrowRight, Database, Scale, ShieldCheck } from "lucide-react";
import { CycleRibbon, StateCartogram } from "@/components/data-visuals";
import { ElectionCard } from "@/components/election-card";
import { LeadPhoto, PhotoEssay } from "@/components/editorial-media";
import { StateSelector } from "@/components/state-selector";
import { Button } from "@/components/ui/button";
import { data, elections, states } from "@/lib/data";

export default function Home() {
  const upcoming = elections.filter((e) => e.election_type === "primary").slice(0, 3);
  const stats = [[elections.length, "verified records"], [states.length, "states + DC"], [new Set(elections.map((e) => e.source_url)).size, "official sources"], ["Nov 3", "general election"]];
  return <>
    <section className="border-b">
      <div className="mx-auto grid max-w-[100rem] md:grid-cols-[1.08fr_.92fr]">
        <div className="paper-grid flex flex-col justify-center gap-7 px-5 py-16 md:px-10 md:py-24 xl:pl-[max(2rem,calc((100vw-80rem)/2))]">
          <p className="rule-label text-secondary">The 2026 midterm cycle · civic reference no. 01</p>
          <h1 className="max-w-4xl text-balance font-serif text-5xl font-bold leading-[.98] tracking-tight md:text-7xl">Every election date, held to a higher standard.</h1>
          <p className="max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground">Midterm Watch tracks official election dates and voter deadlines back to their source—so the civic calendar stays straight, legible, and accountable.</p>
          <div className="max-w-lg"><StateSelector /></div>
        </div>
        <LeadPhoto />
      </div>
    </section>

    <section className="border-b bg-primary text-primary-foreground">
      <div className="mx-auto grid max-w-7xl grid-cols-2 divide-x divide-primary-foreground/20 px-5 md:grid-cols-4 lg:px-8">
        {stats.map(([number, label]) => <div key={label} className="px-4 py-6"><strong className="font-serif text-3xl text-secondary">{number}</strong><span className="mt-1 block rule-label text-primary-foreground/70">{label}</span></div>)}
      </div>
    </section>

    <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8">
      <div className="flex flex-col justify-between gap-4 border-b pb-6 md:flex-row md:items-end"><div><p className="rule-label">Cycle at a glance</p><h2 className="mt-2 font-serif text-4xl font-bold">The road to November</h2></div><p className="max-w-md text-sm text-muted-foreground">A compact view of the reviewed dates in this edition—not a forecast, but an accountable calendar.</p></div>
      <CycleRibbon />
    </section>

    <PhotoEssay />

    <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8">
      <div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr]"><div><p className="rule-label">The national desk</p><h2 className="mt-2 text-balance font-serif text-4xl font-bold">Start with a state. Follow every date to its source.</h2><p className="mt-4 text-muted-foreground">The cartogram is a navigation tool, not a geographic map. Each tile opens the state desk and its reviewed election records.</p><Button asChild className="mt-6"><Link href="/states/">Browse all states <ArrowRight data-icon="inline-end" /></Link></Button></div><StateCartogram /></div>
    </section>

    <section className="border-y bg-card"><div className="mx-auto max-w-7xl px-5 py-20 lg:px-8"><div className="flex items-end justify-between border-b pb-6"><div><p className="rule-label">Next on the calendar</p><h2 className="mt-2 font-serif text-4xl font-bold">Upcoming primaries</h2></div><Link href="/states/" className="editorial-link hidden text-sm md:block">Full state index</Link></div><div className="mt-8 grid gap-5 md:grid-cols-3">{upcoming.map((e, index) => <ElectionCard key={e.id} election={e} featured={index === 0} />)}</div></div></section>

    <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8"><div className="grid gap-8 md:grid-cols-3">{[[ShieldCheck, "Source first", "Every published date points to an official election authority."], [Scale, "Confidence stated", "Our confidence level is visible, with uncertainty never hidden."], [Database, "Open by design", "Download the underlying CSV and JSON used to build this edition."]].map(([Icon, title, copy]) => { const Mark = Icon as typeof ShieldCheck; return <div key={String(title)} className="border-t-2 border-secondary pt-5"><Mark className="size-6 text-secondary" aria-hidden="true"/><h3 className="mt-4 font-serif text-2xl font-bold">{String(title)}</h3><p className="mt-2 text-sm text-muted-foreground">{String(copy)}</p></div>; })}</div><p className="mt-12 text-center font-mono text-xs text-muted-foreground">Edition {data.edition} · Generated {new Date(data.generated_at).toLocaleDateString("en-US", { dateStyle: "long" })}</p></section>
  </>;
}
