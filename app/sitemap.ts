import type { MetadataRoute } from "next";
export const dynamic = "force-static";
import { electionHref, elections, stateHref, states } from "@/lib/data";
export default function sitemap():MetadataRoute.Sitemap{const base="https://midtermwatch.com";return ["","/states/","/methodology/","/data/","/about/"].map(url=>({url:base+url,lastModified:new Date()})).concat(states.map(([code])=>({url:base+stateHref(code),lastModified:new Date()})),elections.map(e=>({url:base+electionHref(e),lastModified:new Date()})));}
