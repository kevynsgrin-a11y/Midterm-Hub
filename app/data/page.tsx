import type { Metadata } from "next";
import { Database, Download, FileJson2, Sheet, CalendarDays } from "lucide-react";
import { Button } from "@/components/ui/button";
import { data, elections } from "@/lib/data";
import { downloadHref, downloads, formatBytes } from "@/lib/downloads";

export const metadata: Metadata = { title: "Open election data", description: "Download and inspect Midterm Watch election records and provenance metadata." };

const icons = { JSON: FileJson2, CSV: Sheet, ICS: CalendarDays } as const;

export default function DataPage() {
  const stats: [number, string][] = [
    [elections.length, "records"],
    [new Set(elections.map((e) => e.state)).size, "jurisdictions"],
    [new Set(elections.map((e) => e.source_url)).size, "source documents"],
  ];
  return <div className="mx-auto max-w-6xl px-5 py-16 lg:px-8">
    <p className="rule-label">Open data / {data.edition}</p>
    <h1 className="mt-3 font-serif text-5xl font-bold">Built to be inspected.</h1>
    <p className="mt-5 max-w-2xl text-lg text-muted-foreground">The same reviewed records that power this site are available in portable formats. Every row retains its source URL and confidence.</p>
    <div className="mt-12 grid gap-5 md:grid-cols-3">
      {downloads.map((file) => {
        const Icon = icons[file.format];
        return <section key={file.name} className="border bg-card p-6">
          <Icon className="text-secondary" aria-hidden="true" />
          <h2 className="mt-5 font-serif text-2xl font-bold">{file.format}</h2>
          <p className="mt-2 text-sm text-muted-foreground">{file.description}</p>
          <Button asChild className="mt-6"><a href={downloadHref(file.name)} download><Download aria-hidden="true" /> Download {file.format}</a></Button>
          <p className="mt-4 font-mono text-xs text-muted-foreground">{file.records} {file.format === "ICS" ? "upcoming elections" : "records"} · {formatBytes(file.bytes)}</p>
          <p className="mt-1 break-all font-mono text-[11px] text-muted-foreground">SHA-256 {file.sha256}</p>
        </section>;
      })}
    </div>
    <div className="mt-12 grid gap-px bg-border md:grid-cols-3">
      {stats.map(([n, l]) => <div key={l} className="bg-primary p-7 text-primary-foreground"><strong className="font-serif text-4xl text-secondary">{n}</strong><span className="block rule-label text-primary-foreground/70">{l}</span></div>)}
    </div>
    <div className="mt-12 flex gap-4 border-l-4 border-secondary bg-card p-6">
      <Database className="shrink-0 text-secondary" aria-hidden="true" />
      <p className="text-sm text-muted-foreground">Generated {new Date(data.generated_at).toLocaleString("en-US", { dateStyle: "long", timeStyle: "short" })}. Each file is rebuilt from the same reviewed records on every release, and the SHA-256 above lets you check a download against this page. The calendar lists only elections on or after that date.</p>
    </div>
  </div>;
}
