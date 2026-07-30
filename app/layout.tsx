import type { Metadata, Viewport } from "next";
import { DM_Sans, Fraunces } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
const dm=DM_Sans({subsets:["latin"],variable:"--font-dm"});
const fraunces=Fraunces({subsets:["latin"],variable:"--font-fraunces"});
export const metadata:Metadata={metadataBase:new URL("https://midtermwatch.com"),title:{default:"Midterm Watch — 2026 Election Dates",template:"%s · Midterm Watch"},description:"A provenance-first reference for official U.S. election dates, voter deadlines, and open civic data.",openGraph:{type:"website",siteName:"Midterm Watch",title:"Midterm Watch — 2026 Election Dates",description:"Official election dates, deadlines, and source citations."}};
export const viewport:Viewport={themeColor:[{media:"(prefers-color-scheme: light)",color:"#f5f4f2"},{media:"(prefers-color-scheme: dark)",color:"#0b1526"}],colorScheme:"light dark"};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en" className={`${dm.variable} ${fraunces.variable} bg-background`}><body><SiteHeader/><main id="main">{children}</main><SiteFooter/></body></html>}
