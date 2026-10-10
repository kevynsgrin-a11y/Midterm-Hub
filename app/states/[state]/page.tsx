import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ElectionCard } from "@/components/election-card";
import { CountdownMasthead } from "@/components/data-art";
import { Button } from "@/components/ui/button";
import { formatDate, forState, stateNames, states } from "@/lib/data";
import { localCalendarDate } from "@/lib/calendar";
export const dynamicParams=false;
export function generateStaticParams(){return states.map(([state])=>({state:state.toLowerCase()}));}
// Title matches the arriving demand: GSC (Sep 2026) queries are
// "<state> election dates 2026" and "<state> midterm elections 2026" —
// the old "<state> election calendar" missed the "dates" phrasing.
export async function generateMetadata({params}:{params:Promise<{state:string}>}):Promise<Metadata>{const raw=await params;const code=raw.state.toUpperCase();const name=stateNames[code];if(!name)return{title:"State election calendar",description:"Verified 2026 midterm election dates and voter deadlines."};
// GSC (Oct 2026) question-intent queries — "when is <state> midterm elections 2026",
// "when is governor election" — land on this page at 6-10 without clicking.
// Answer the general-election date in the snippet, from the verified store only.
const general=forState(code).find((e)=>/general/i.test(e.election_type)&&e.election_date>="2026-01-01");
if(!general)return{title:`${name} Election Dates 2026 — Voter Deadlines`,description:`Verified 2026 midterm election dates, voter registration deadlines, and official sources for ${name}.`};
let description=`${name}'s 2026 general election is ${formatDate(general.election_date)}.`;
if(general.registration_deadline)description+=` Registration closes ${formatDate(general.registration_deadline,true)}.`;
if(general.mail_ballot_request_deadline)description+=` Mail-ballot requests ${formatDate(general.mail_ballot_request_deadline,true)}.`;
const full=`${description} Verified from official sources.`;
return{title:`${name} Election Dates 2026 — Voter Deadlines`,description:full.length<=155?full:`${name}'s 2026 general election is ${formatDate(general.election_date)}. Verified from official sources.`};}
export default async function StatePage({params}:{params:Promise<{state:string}>}){const raw=await params;const state=raw.state.toUpperCase();const items=forState(state);const name=stateNames[state];if(!name)notFound();const today=localCalendarDate();const focus=items.find(e=>e.election_date>=today)??items[items.length-1];return <div className="mx-auto max-w-7xl px-5 py-14 lg:px-8"><nav className="rule-label"><Link href="/states/">States</Link> / {state}</nav><div className="mt-8 grid gap-8 border-b pb-10 md:grid-cols-[1fr_auto] md:items-end"><div><p className="rule-label">State desk / {state}</p><h1 className="mt-2 font-serif text-5xl font-bold">{name}</h1><p className="mt-4 text-lg text-muted-foreground">{items.length} reviewed election {items.length===1?"record":"records"} in the current edition.</p></div><Button asChild variant="outline"><a href={items[0]?.source_url} target="_blank" rel="noreferrer">Visit election authority</a></Button></div>{focus&&<CountdownMasthead className="mt-10" date={focus.election_date} initialDate={today} eyebrow={`State desk · next up`} caption={`${name}'s next reviewed election in this edition: ${focus.jurisdiction_name}, ${formatDate(focus.election_date)}. Registration and early-voting deadlines for it are listed below with their sources.`} />}{items.length?<div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">{items.map((e,i)=><ElectionCard key={e.id} election={e} featured={i===0}/>)}</div>:<div className="mt-10 border bg-card p-8"><h2 className="font-serif text-2xl font-bold">No verified dates yet</h2><p className="mt-2 text-muted-foreground">We publish only after a source can support the record.</p></div>}</div>}
