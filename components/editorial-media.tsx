import Image from "next/image";
import { cn } from "@/lib/utils";

type EditorialImageProps = {
  src: string;
  alt: string;
  eyebrow: string;
  caption: string;
  priority?: boolean;
  className?: string;
  imageClassName?: string;
  frameClassName?: string;
  sizes?: string;
};

export function EditorialImage({ src, alt, eyebrow, caption, priority = false, className, imageClassName, frameClassName, sizes = "(min-width: 1024px) 50vw, 100vw" }: EditorialImageProps) {
  return (
    <figure className={cn("group", className)}>
      <div className={cn("relative aspect-[4/3] overflow-hidden bg-muted", frameClassName)}>
        <Image
          src={src}
          alt={alt}
          fill
          priority={priority}
          sizes={sizes}
          className={cn("object-cover transition-transform duration-700 motion-reduce:transition-none group-hover:scale-[1.015]", imageClassName)}
        />
      </div>
      <figcaption className="flex flex-col gap-2 border-x border-b bg-card p-4 sm:flex-row sm:items-start sm:justify-between">
        <span className="rule-label text-secondary">{eyebrow}</span>
        <span className="max-w-md text-sm leading-relaxed text-muted-foreground">{caption}</span>
      </figcaption>
    </figure>
  );
}

export function LeadPhoto() {
  return (
    <figure className="group relative min-h-[24rem] overflow-hidden bg-primary md:min-h-[36rem]">
      <Image
        src="/images/election/rally-crowd.png"
        alt="A diverse crowd gathers at a nonpartisan community rally with civic signs raised."
        fill
        priority
        sizes="(min-width: 768px) 48vw, 100vw"
        className="object-cover transition-transform duration-700 motion-reduce:transition-none group-hover:scale-[1.015]"
      />
      <figcaption className="absolute inset-x-0 bottom-0 bg-primary/95 p-5 text-primary-foreground backdrop-blur-sm md:max-w-md">
        <span className="rule-label text-secondary">On the ground</span>
        <p className="mt-2 text-sm leading-relaxed">The civic calendar is lived in crowded rooms, long field days, and communities asking to be heard.</p>
      </figcaption>
    </figure>
  );
}

export function PhotoEssay() {
  return (
    <section className="border-y bg-primary text-primary-foreground">
      <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8">
        <div className="grid gap-8 md:grid-cols-[.72fr_1.28fr] md:items-end">
          <div>
            <p className="rule-label text-secondary">Two sides of election night</p>
            <h2 className="mt-3 text-balance font-serif text-4xl font-bold md:text-5xl">The human race. The data race.</h2>
          </div>
          <p className="max-w-2xl text-pretty text-primary-foreground/75 md:justify-self-end">Campaigns move through conversations and crowded rooms. Public understanding moves through verified feeds, careful analysis, and the people watching every signal.</p>
        </div>
        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          <EditorialImage src="/images/election/constituent-listening.png" alt="A community leader listens to constituents seated in a civic hall." eyebrow="The public square" caption="Before a race becomes a chart, it is a conversation between people and those asking to represent them." imageClassName="object-[center_42%]" />
          <EditorialImage src="/images/election/polling-streams.png" alt="Election analysts monitor abstract polling and turnout dashboards in an operations room." eyebrow="The signal room" caption="Behind the public numbers, analysts reconcile streams, watch for anomalies, and keep the record legible." />
        </div>
        <div className="mt-6 grid gap-6 md:grid-cols-3">
          <EditorialImage src="/images/election/campaign-advisor.png" alt="A campaign advisor takes a phone call while working through election-day paperwork." eyebrow="Field work" caption="Calls, calendars, and decisions made against the clock." sizes="(min-width: 768px) 33vw, 100vw" />
          <EditorialImage src="/images/election/ballot-box.png" alt="A voter places a paper ballot into a secured ballot box at a polling place." eyebrow="The vote" caption="The physical act at the center of every result." sizes="(min-width: 768px) 33vw, 100vw" />
          <EditorialImage src="/images/election/race-dashboard.png" alt="A data journalist reviews an abstract mock election dashboard across two screens." eyebrow="The readout" caption="Structured data turns a fast-moving race into a record that can be checked." sizes="(min-width: 768px) 33vw, 100vw" />
        </div>
      </div>
    </section>
  );
}
