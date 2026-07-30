import type { Metadata } from "next";
import Image from "next/image";

export const metadata: Metadata = {
  title: "Logo preview",
  description: "Temporary comparison of Midterm Watch logo concepts.",
  robots: { index: false, follow: false },
};

const options = [
  {
    id: 1,
    name: "Option 1 — Election Calendar",
    note: "Calendar grid with a highlighted red election day. Most literal to the election-date purpose and cleanest at small sizes.",
    src: "/images/brand/logo-option-1.png",
  },
  {
    id: 2,
    name: "Option 2 — Watchful Ballot Eye",
    note: "An eye formed around a checkmarked ballot, emphasizing the 'Watch' monitoring theme. Distinctive but busier.",
    src: "/images/brand/logo-option-2.png",
  },
  {
    id: 3,
    name: "Option 3 — Civic Shield Roundel",
    note: "Shield of bars with a red plumbline pointer, blending data and civic authority into a crest.",
    src: "/images/brand/logo-option-3.png",
  },
];

function MockHeader({ src, dark }: { src: string; dark?: boolean }) {
  return (
    <div className={dark ? "dark" : ""}>
      <div className="flex items-center justify-between border border-border bg-background px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="relative flex size-9 items-center justify-center overflow-hidden">
            <Image src={src || "/placeholder.svg"} alt="Logo concept in header" fill className="object-contain" sizes="36px" />
          </span>
          <span>
            <strong className="block font-serif text-xl leading-none text-foreground">Midterm Watch</strong>
            <span className="text-[0.7rem] uppercase tracking-widest text-muted-foreground">Election date reference</span>
          </span>
        </div>
        <span className="text-sm text-muted-foreground">States</span>
      </div>
    </div>
  );
}

export default function BrandPreviewPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <header className="mb-12">
        <p className="text-sm uppercase tracking-widest text-secondary">Temporary preview</p>
        <h1 className="mt-2 font-serif text-4xl font-bold text-balance">Midterm Watch logo concepts</h1>
        <p className="mt-3 max-w-2xl leading-relaxed text-muted-foreground">
          Each concept is shown on its own, then inside a header on light and dark surfaces. Tell me the option number to
          finalize; this page will be removed afterward.
        </p>
      </header>

      <div className="flex flex-col gap-16">
        {options.map((opt) => (
          <section key={opt.id} className="flex flex-col gap-6">
            <div>
              <h2 className="font-serif text-2xl font-bold">{opt.name}</h2>
              <p className="mt-1 max-w-2xl leading-relaxed text-muted-foreground">{opt.note}</p>
            </div>
            <div className="grid gap-6 md:grid-cols-3">
              <div className="flex items-center justify-center border border-border bg-card p-8">
                <div className="relative size-32">
                  <Image src={opt.src || "/placeholder.svg"} alt={opt.name} fill className="object-contain" sizes="128px" />
                </div>
              </div>
              <MockHeader src={opt.src} />
              <MockHeader src={opt.src} dark />
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
